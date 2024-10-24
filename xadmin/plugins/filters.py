# coding=utf-8
import operator
import urllib.parse
from functools import reduce

from django.contrib.admin.utils import get_fields_from_path
try:
	from django.contrib.admin.utils import lookup_spawns_duplicates as lookup_needs_distinct
except ImportError:
	from django.contrib.admin.utils import lookup_needs_distinct
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured, ValidationError, FieldDoesNotExist
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.template import loader
from django.template.loader import render_to_string
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _

from xadmin import widgets
from xadmin.filters import manager as filter_manager, FILTER_PREFIX, SEARCH_VAR
from xadmin.plugins.utils import get_context_dict
from xadmin.sites import site
from xadmin.util import is_related_field, get_model_from_relation
from xadmin.views import BaseAdminPlugin, ListAdminView


class IncorrectLookupParameters(Exception):
	pass


class FilterPlugin(BaseAdminPlugin):
	list_filter = ()
	search_fields = ()
	free_query_filter = True

	def lookup_allowed(self, lookup, value):
		model = self.model
		# Check FKey lookups that are allowed, so that popups produced by
		# ForeignKeyRawIdWidget, on the basis of ForeignKey.limit_choices_to,
		# are allowed to work.
		for l in model._meta.related_fkey_lookups:
			for k, v in widgets.url_params_from_lookup_dict(l).items():
				if k == lookup and v == value:
					return True

		parts = lookup.split(LOOKUP_SEP)

		# Last term in lookup is a query term (__exact, __startswith etc)
		# This term can be ignored.
		# if len(parts) > 1 and parts[-1] in QUERY_TERMS:
		#     parts.pop()

		# Special case -- foo__id__exact and foo__id queries are implied
		# if foo has been specificially included in the lookup list; so
		# drop __id if it is the last part. However, first we need to find
		# the pk attribute name.
		rel_name = None
		for part in parts[:-1]:
			try:
				field = model._meta.get_field(part)
			except FieldDoesNotExist:
				# Lookups on non-existants fields are ok, since they're ignored
				# later.
				return True
			if hasattr(field, 'remote_field'):
				model = field.remote_field.model
				rel_name = field.remote_field.get_related_field().name
			elif is_related_field(field):
				model = field.model
				rel_name = model._meta.pk.name
			else:
				rel_name = None
		if rel_name and len(parts) > 1 and parts[-1] == rel_name:
			parts.pop()

		if len(parts) == 1:
			return True
		clean_lookup = LOOKUP_SEP.join(parts)
		return clean_lookup in self.list_filter

	@staticmethod
	def get_related_title(field, default):
		"""Attempts to extract the verbose name from a related field"""
		if isinstance(field, models.ForeignKey):  # ForeignKey / verbose_name
			verbose_name = getattr(field, "verbose_name", default) or default
		elif isinstance(field, (models.OneToOneRel, models.OneToOneField)):
			if field.auto_created and field.related_model:
				opts = get_model_from_relation(field)._meta
			else:
				opts = field
			verbose_name = getattr(opts, "verbose_name", default) or default
		else:
			verbose_name = default
		return verbose_name

	def _fsearch_url_params(self, queryset: models.QuerySet, params: dict) -> models.QuerySet:
		"""Filters parameters passed to another view (fk_search)"""
		try:
			lookup_params = {}
			lookups = ("__in",)
			for key, value in params.items():
				value_list = value.split(',')
				if len(value_list) > 0 and any([key.endswith(lookup) for lookup in lookups]):
					lookup_params[key] = value_list
				else:
					lookup_params[key] = value
			if lookup_params:
				queryset = queryset.filter(**lookup_params)
		except (SuspiciousOperation, ImproperlyConfigured):
			raise
		except Exception as e:
			raise IncorrectLookupParameters(e)
		return queryset

	def get_list_queryset(self, queryset):
		lookup_params = dict([(smart_str(k)[len(FILTER_PREFIX):], v) for k, v in self.admin_view.params.items()
		                      if smart_str(k).startswith(FILTER_PREFIX) and v != ''])
		for p_key, p_val in lookup_params.items():
			if p_val == "False":
				lookup_params[p_key] = False
		use_distinct = False

		# for clean filters
		self.admin_view.has_query_param = bool(lookup_params)
		self.admin_view.clean_query_url = self.admin_view.get_query_string(remove=[k for k in self.request.GET.keys() if
		                                                                           k.startswith(FILTER_PREFIX)])

		# Normalize the types of keys
		if not self.free_query_filter:
			for key, value in lookup_params.items():
				if not self.lookup_allowed(key, value):
					raise SuspiciousOperation(
						"Filtering by %s not allowed" % key)

		self.filter_specs = []
		if self.list_filter:
			for list_filter in self.list_filter:
				if callable(list_filter):
					# This is simply a custom list filter class.
					spec = list_filter(self.request, lookup_params,
					                   self.model, self)
				else:
					field_path = None
					field_parts = []
					if isinstance(list_filter, (tuple, list)):
						# This is a custom FieldListFilter class for a given field.
						field, field_list_filter_class = list_filter
					else:
						# This is simply a field name, so use the default
						# FieldListFilter class that has been registered for
						# the type of the given field.
						field, field_list_filter_class = list_filter, filter_manager.create
					if not isinstance(field, models.Field):
						field_path = field
						field_parts = get_fields_from_path(self.model, field_path)
						field = field_parts[-1]
					spec = field_list_filter_class(
						field, self.request, lookup_params,
						self.model, self.admin_view, field_path=field_path)

					if len(field_parts) > 1:
						# Add related model name to title
						field_part = field_parts[-2]
						field_part_name = field_part.name
						field_part_name = self.get_related_title(field_part, field_part_name)
						spec.title = render_to_string("xadmin/filters/arrow.html", context={
							'name': field_part_name,
							'title': spec.title
						})

					# Check if we need to use distinct()
					use_distinct = (use_distinct or lookup_needs_distinct(self.opts, field_path))
				if spec and spec.has_output():
					try:
						new_qs = spec.do_filter(queryset)
					except ValidationError as e:
						new_qs = None
						self.admin_view.message_user(_("<b>Filtering error:</b> %s") % e.messages[0], 'error')
					if new_qs is not None:
						queryset = new_qs

					self.filter_specs.append(spec)

		self.has_filters = bool(self.filter_specs)
		self.admin_view.filter_specs = self.filter_specs
		obj = [fspec for fspec in self.filter_specs if fspec.is_used]
		self.admin_view.used_filter_num = len(obj)

		try:
			for key, value in lookup_params.items():
				use_distinct = (use_distinct or lookup_needs_distinct(self.opts, key))
		except FieldDoesNotExist as e:
			raise IncorrectLookupParameters(e)

		if isinstance(queryset, models.QuerySet) and lookup_params:
			queryset = self._fsearch_url_params(queryset, lookup_params)

		query = urllib.parse.unquote_plus(self.request.GET.get(SEARCH_VAR, ''))

		# Apply keyword searches.
		def construct_search(field_name):
			if field_name.startswith('^'):
				return "%s__istartswith" % field_name[1:]
			elif field_name.startswith('='):
				return "%s__iexact" % field_name[1:]
			elif field_name.startswith('@'):
				return "%s__search" % field_name[1:]
			else:
				return "%s__icontains" % field_name

		if self.search_fields and query:
			orm_lookups = [construct_search(str(search_field))
			               for search_field in self.search_fields]
			for bit in query.split():
				or_queries = [models.Q(**{orm_lookup: bit})
				              for orm_lookup in orm_lookups]
				queryset = queryset.filter(reduce(operator.or_, or_queries))
			if not use_distinct:
				for search_spec in orm_lookups:
					if lookup_needs_distinct(self.opts, search_spec):
						use_distinct = True
						break
		self.admin_view.search_query = query

		if use_distinct:
			return queryset.distinct()
		else:
			return queryset

	# Media
	def get_media(self, media):
		for fspec in self.filter_specs:
			try:
				media += fspec.get_media()
			except NotImplementedError:
				continue
		return media + self.vendor('xadmin.plugin.filters.js')

	# Block Views
	def block_nav_menu(self, context, nodes):
		if self.has_filters:
			nodes.append(loader.render_to_string('xadmin/blocks/model_list.nav_menu.filters.html',
			                                     context=get_context_dict(context)))

	def block_nav_form(self, context, nodes):
		if self.search_fields:
			context = get_context_dict(context or {})  # no error!
			context.update({
				'search_var': SEARCH_VAR,
				'remove_search_url': self.admin_view.get_query_string(remove=[SEARCH_VAR]),
				'search_form_params': self.admin_view.get_form_params(remove=[SEARCH_VAR])
			})
			nodes.append(
				loader.render_to_string(
					'xadmin/blocks/model_list.nav_form.search_form.html',
					context=context)
			)


site.register_plugin(FilterPlugin, ListAdminView)
