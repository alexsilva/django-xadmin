# coding=UTF-8
from itertools import chain

from django.db.models.options import PROXY_PARENTS
from django.db.models.sql.query import LOOKUP_SEP
from django.template.loader import render_to_string
from django.urls.base import reverse
from django.utils.encoding import force_str
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe

from xadmin.sites import site
from xadmin.util import is_related_field2
from xadmin.views import BaseAdminPlugin, ListAdminView, CreateAdminView, UpdateAdminView, DeleteAdminView

RELATE_PREFIX = '_rel_'


class RelateMenuPlugin(BaseAdminPlugin):
	related_list = []
	use_related_menu = True

	def _get_all_related_objects(self, local_only=False, include_hidden=False,
	                             include_proxy_eq=False):
		"""
		Returns a list of related fields (also many to many)
		:param local_only:
		:param include_hidden:
		:return: list
		"""
		include_parents = True if local_only is False else PROXY_PARENTS
		fields = self.opts._get_fields(
			forward=False, reverse=True,
			include_parents=include_parents,
			include_hidden=include_hidden
		)
		if include_proxy_eq:
			children = chain.from_iterable(c._relation_tree
			                               for c in self.opts.concrete_model._meta.proxied_children
			                               if c is not self.opts)
			relations = (f.remote_field for f in children
			             if include_hidden or not f.remote_field.field.remote_field.is_hidden())
			fields = chain(fields, relations)
		return list(fields)

	def get_related_list(self):
		if hasattr(self, '_related_acts'):
			return self._related_acts

		_related_acts = []
		for rel in self._get_all_related_objects():
			if self.related_list and (rel.get_accessor_name() not in self.related_list):
				continue
			if rel.related_model not in self.admin_site._registry.keys():
				continue
			has_view_perm = self.has_model_perm(rel.related_model, 'view')
			has_add_perm = self.has_model_perm(rel.related_model, 'add')
			if not (has_view_perm or has_add_perm):
				continue

			_related_acts.append((rel, has_view_perm, has_add_perm))

		self._related_acts = _related_acts
		return self._related_acts

	def related_link(self, instance):
		menu_links = []
		for rel, view_perm, add_perm in self.get_related_list():
			opts = rel.related_model._meta

			label = opts.app_label
			model_name = opts.model_name

			field = rel.field
			rel_name = rel.get_related_field().name

			verbose_name = force_str(opts.verbose_name)
			lookup_name = '%s__%s__exact' % (field.name, rel_name)

			menu = {
				'view_link': {
					'has_perm': view_perm,
					'title': verbose_name
				},
				'add_link': {
					'has_perm': add_perm
				}
			}
			if view_perm:
				menu['view_link']['url'] = reverse(
					'%s:%s_%s_changelist' % (self.admin_site.app_name, label, model_name))
				menu['view_link']['url'] += "?%(query)s=%(pk)s" % {
					'query': RELATE_PREFIX + lookup_name,
					'pk': instance.pk
				}
			if add_perm:
				menu['add_link']['url'] = reverse('%s:%s_%s_add' % (self.admin_site.app_name, label, model_name))
				menu['add_link']['url'] += "?%(query)s=%(pk)s" % {
					'query': RELATE_PREFIX + lookup_name,
					'pk': instance.pk
				}

			menu_links.append(menu)
		return render_to_string('xadmin/plugins/related_links.html', context={'menu_links': menu_links})

	related_link.short_description = '&nbsp;'
	related_link.allow_tags = True
	related_link.allow_export = False
	related_link.is_column = False

	def get_list_display(self, list_display):
		if self.use_related_menu and len(self.get_related_list()):
			list_display.append('related_link')
			self.admin_view.related_link = self.related_link
		return list_display


class RelateObject:

	def __init__(self, admin_view, lookup, value):
		self.admin_view = admin_view
		self.org_model = admin_view.model
		self.opts = admin_view.opts
		self.lookup = lookup
		self.value = value

		parts = lookup.split(LOOKUP_SEP)
		field = self.opts.get_field(parts[0])

		if not is_related_field2(field):
			raise Exception('Relate Lookup field must a related field')

		self.to_model = field.related_model
		self.rel_name = '__'.join(parts[1:])
		self.is_m2m = bool(field.many_to_many)

		to_qs = self.to_model._default_manager.get_queryset()
		self.to_objs = to_qs.filter(**{self.rel_name: value}).all()

		self.field = field

	def filter(self, queryset):
		return queryset.filter(**{self.lookup: self.value})

	def get_brand_name(self):
		if len(self.to_objs) == 1:
			to_model_name = str(self.to_objs[0])
		else:
			to_model_name = force_str(self.to_model._meta.verbose_name)

		return mark_safe("<span class='rel-brand'>%s <i class='fa fa-caret-right'></i></span> %s" % (
		to_model_name, force_str(self.opts.verbose_name_plural)))


class BaseRelateDisplayPlugin(BaseAdminPlugin):

	def init_request(self, *args, **kwargs):
		self.relate_obj = None
		for k, v in self.request.GET.items():
			if smart_str(k).startswith(RELATE_PREFIX):
				self.relate_obj = RelateObject(
					self.admin_view, smart_str(k)[len(RELATE_PREFIX):], v)
				break
		return bool(self.relate_obj)

	def _get_relate_params(self):
		return RELATE_PREFIX + self.relate_obj.lookup, self.relate_obj.value

	def _get_input(self):
		return '<input type="hidden" name="%s" value="%s" />' % self._get_relate_params()

	def _get_url(self, url):
		return url + ('&' if url.find('?') > 0 else '?') + ('%s=%s' % self._get_relate_params())


class ListRelateDisplayPlugin(BaseRelateDisplayPlugin):

	def get_list_queryset(self, queryset):
		if self.relate_obj:
			queryset = self.relate_obj.filter(queryset)
		return queryset

	def url_for_result(self, url, result):
		return self._get_url(url)

	def get_context(self, context):
		context['brand_name'] = self.relate_obj.get_brand_name()
		context['rel_objs'] = self.relate_obj.to_objs
		if len(self.relate_obj.to_objs) == 1:
			context['rel_obj'] = self.relate_obj.to_objs[0]
		if 'add_url' in context:
			context['add_url'] = self._get_url(context['add_url'])
		return context

	def get_list_display(self, list_display):
		if not self.relate_obj.is_m2m:
			try:
				list_display.remove(self.relate_obj.field.name)
			except Exception:
				pass
		return list_display


class EditRelateDisplayPlugin(BaseRelateDisplayPlugin):

	def get_form_datas(self, datas):
		if self.admin_view.org_obj is None and self.admin_view.request_method == 'get':
			datas['initial'][
				self.relate_obj.field.name] = self.relate_obj.value
		return datas

	def post_response(self, response):
		if isinstance(response, str) and response != self.get_admin_url('index'):
			return self._get_url(response)
		return response

	def get_context(self, context):
		if 'delete_url' in context:
			context['delete_url'] = self._get_url(context['delete_url'])
		return context

	def block_after_fieldsets(self, context, nodes):
		return self._get_input()


class DeleteRelateDisplayPlugin(BaseRelateDisplayPlugin):

	def post_response(self, response):
		if isinstance(response, str) and response != self.get_admin_url('index'):
			return self._get_url(response)
		return response

	def block_form_fields(self, context, nodes):
		return self._get_input()


site.register_plugin(RelateMenuPlugin, ListAdminView)
site.register_plugin(ListRelateDisplayPlugin, ListAdminView)
site.register_plugin(EditRelateDisplayPlugin, CreateAdminView)
site.register_plugin(EditRelateDisplayPlugin, UpdateAdminView)
site.register_plugin(DeleteRelateDisplayPlugin, DeleteAdminView)
