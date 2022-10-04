# coding=utf-8
import copy
import hashlib
import re
import time
import urllib.parse

from django import forms
from django.db import models
from django.forms.models import modelform_factory
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.core.exceptions import FieldDoesNotExist

from xadmin.filters import SEARCH_VAR
from xadmin.layout import Layout
from xadmin.sites import site
from xadmin.util import get_model_from_relation, vendor
from xadmin.views import BaseAdminPlugin, ModelFormAdminView

QUICKFORM_0_VAR = "_qfrm0"


class QuickFormPrefix:
	"""Generates a prefix + md5 hash (based on time) that avoids conflict with main form ids"""

	def __init__(self, name, length=None):
		self.name = name
		self.regex = re.compile(rf"({re.escape(name)}-[a-z0-9]+)")
		self.regex_generic = re.compile(r'(\w+[-_]\d+)-\w+$')
		self.length = length if length else 5

	@cached_property
	def hash(self):
		"""hash prefix"""
		hs = hashlib.md5(force_bytes(time.time()))
		return f"{self.name}-{hs.hexdigest()[:self.length]}"

	def resolve(self, data):
		"""Finds the prefix of a form's data"""
		for key in data:
			match = self.regex.match(key)
			if match:
				return match.groups()[0]
		else:
			for key in data:
				match = self.regex_generic.match(key)
				if match:
					return match.groups()[0]

	def clean(self, fields):
		"""Remove prefixes from the form field"""
		prefix = self.resolve(fields)
		if prefix is None:
			return fields
		return [f.replace(prefix, "").lstrip("-") for f in fields]

	def __str__(self):
		return self.hash


class QuickFormPlugin(BaseAdminPlugin):

	def init_request(self, *args, **kwargs):
		self.request_params = self.request.GET
		return bool(self.request.method == 'GET' and
		            self.request_params.get(SEARCH_VAR) is None and
		            self.request_params.get(QUICKFORM_0_VAR) is None and
		            self.request.is_ajax() or
		            self.request_params.get('_ajax'))

	def setup(self, *args, **kwargs):
		self.admin_view.add_form_template = 'xadmin/views/quick_form.html'
		self.admin_view.change_form_template = 'xadmin/views/quick_form.html'
		self.prefix = QuickFormPrefix(f'quickform-{self.opts.app_label}-{self.opts.model_name}')

	def get_model_form(self, __, **kwargs):
		if '_field' in self.request_params:
			fields = self.request_params['_field'].split(',')
			defaults = {
				"form": self.admin_view.form,
				"fields": self.prefix.clean(fields),
				"formfield_callback": self.admin_view.formfield_for_dbfield,
			}
			form = modelform_factory(self.model, **defaults)
			form.prefix = self.prefix.resolve(self.request_params)
		else:
			form = __()
			form.prefix = str(self.prefix)
		return form

	def get_form_layout(self, __):
		if '_field' in self.request_params:
			fields = self.request_params['_field'].split(',')
			return Layout(*self.prefix.clean(fields))
		return __()

	def get_context(self, context):
		context['form_url'] = self.request.path
		return context

	def get_form_datas(self, datas):
		if self.admin_view.request_method == 'get' and '_field' in self.request_params:
			initial = datas.setdefault('initial', {})
			fields = self.request_params["_field"].split(',')
			initial_new = {}
			for key in fields:
				key_prefix = key
				if self.admin_view.model_form.prefix:
					key = re.sub('^' + re.escape(self.admin_view.model_form.prefix + '-'), '', key)
				try:
					field = self.opts.get_field(key)
				except FieldDoesNotExist:
					continue
				if isinstance(field, models.ManyToManyField):
					initial_new[key] = self.request_params[key_prefix].split(",")
				else:
					# field value without a prefix
					initial_new[key] = self.request_params[key_prefix]
			initial.update(initial_new)
		return datas


class QuickFormFormSetPlugin(BaseAdminPlugin):
	inlineformset_prefix = 'quickformset'

	def init_request(self, *args, **kwargs):
		return bool(isinstance(self.admin_view, ModelFormAdminView) and
		            self.request.GET.get(QUICKFORM_0_VAR) is None and
		            self.request.is_ajax() or
		            self.request.GET.get('_ajax'))

	def get_formset(self, formset, **kwargs):
		self.fk_prefix = formset.get_default_prefix()
		return formset

	def get_model_form(self, form, **kwargs):
		prefix = QuickFormPrefix(f'quickform-{self.opts.app_label}-{self.opts.model_name}')
		if self.request.method == "POST":
			form.prefix = prefix.resolve(self.request.POST)
		return form

	def get_formset_attrs(self, attrs):
		"""Changes the default prefix to not conflict with the default form"""
		prefix = QuickFormPrefix(self.inlineformset_prefix + "-" + self.fk_prefix)
		if self.request.method == "GET":
			attrs['prefix'] = str(prefix)
		else:
			data = attrs.get('data', self.request.POST)
			attrs['prefix'] = prefix.resolve(data)
		return attrs


class RelatedFieldWidgetWrapper(forms.Widget):
	"""
	This class is a wrapper to a given widget to add the add icon for the
	admin interface.
	"""

	def __init__(self, widget, rel, add_url, rel_add_url, change_url=None, rel_change_url=None, **kwargs):
		self.needs_multipart_form = widget.needs_multipart_form
		self.attrs = widget.attrs
		self.choices = widget.choices
		self.is_required = widget.is_required
		self.widget = widget
		self.rel = rel

		self.add_url = add_url
		self.rel_add_url = rel_add_url
		self.change_url = change_url
		self.rel_change_url = rel_change_url

		if hasattr(self, 'input_type'):
			self.input_type = widget.input_type

		self.kwargs = kwargs
		self.request_params = kwargs.pop('request_params', {})

	def __deepcopy__(self, memo):
		obj = copy.copy(self)
		obj.widget = copy.deepcopy(self.widget, memo)
		obj.attrs = self.widget.attrs
		memo[id(self)] = obj
		return obj

	@property
	def media(self):
		media = self.widget.media + vendor('xadmin.plugin.quick-form.js')
		return media

	def resolve_field_name_if_inline(self, name):
		"""When the original field is an inline the name should be changed to the original."""
		new_name = self.request_params.get('_field_inline_' + name)
		return (new_name and new_name[0]) or name

	def render(self, name, value, attrs=None, **kwargs):
		name = self.resolve_field_name_if_inline(name)
		self.widget.choices = self.choices
		output = []
		output.extend(['<div class="d-flex align-items-start input-group quick-form-field">'])
		output.extend(['<div class="flex-grow-1 mr-2" id="id_%s_wrap_container">' % name,
		               self.widget.render(name, value, attrs=attrs, **kwargs), '</div>'])
		if self.change_url:
			html = render_to_string("xadmin/plugins/quickform_btn.html", context={
				'title': _('Change %s') % self.rel.model._meta.verbose_name,
				'editable_url': self.change_url,
				'refresh_url': self.rel_change_url + "?" + urllib.parse.urlencode({'_field': name, name: ''}),
				'for_id': name,
				'icon': 'fa fa-edit',
				'action': 'change'
			})
			output.append(html)
		if self.add_url:
			html = render_to_string("xadmin/plugins/quickform_btn.html", context={
				'title': _('Create New %s') % self.rel.model._meta.verbose_name,
				'editable_url': self.add_url,
				'refresh_url': self.rel_add_url + "?" + urllib.parse.urlencode({'_field': name, name: ''}),
				'for_id': name,
				'icon': 'fa fa-plus',
				'action': 'add'
			})
			output.append(html)
		output.extend(['</div>'])
		return mark_safe(''.join(output))

	def build_attrs(self, extra_attrs=None, **kwargs):
		"Helper function for building an attribute dictionary."
		self.attrs = self.widget.build_attrs(extra_attrs=None, **kwargs)
		return self.attrs

	def value_from_datadict(self, data, files, name):
		return self.widget.value_from_datadict(data, files, name)

	def id_for_label(self, id_):
		return self.widget.id_for_label(id_)


class QuickAddBtnPlugin(BaseAdminPlugin):
	# Allows you to delete fields changed by the plugin
	quick_addbtn_fields_exclude = ()
	# Allows exclude db field like (modes.CharField)
	quick_addbtn_db_fields_exclude = ()
	# Fields that can be edited after being added.
	quick_changebtn_db_fields = ()
	# Always enable
	quick_addbtn_enabled = True

	def init_request(self, *args, **kwargs):
		return self.quick_addbtn_enabled

	def formfield_for_dbfield(self, formfield, db_field, **kwargs):
		if db_field.name in self.quick_addbtn_fields_exclude or \
				isinstance(db_field, self.quick_addbtn_db_fields_exclude):
			return formfield  # disabled to this types
		elif formfield and self.model in self.admin_site._registry and \
				isinstance(db_field, (models.ForeignKey, models.ManyToManyField)) and \
				hasattr(formfield.widget, "choices"):
			rel_model = get_model_from_relation(db_field)
			if rel_model in self.admin_site._registry:
				add_url = rel_add_url = change_url = rel_change_url = None
				if self.has_model_perm(rel_model, 'add'):
					add_url = self.get_model_url(rel_model, 'add')
					rel_add_url = self.get_model_url(self.model, 'add')
				# Configure the editing of foreign key data
				if (self.has_model_perm(rel_model, 'change') and
						isinstance(db_field, models.ForeignKey) and
						db_field.name in self.quick_changebtn_db_fields):
					instance = getattr(self.admin_view, "org_obj", None)
					rel_instance = instance and getattr(instance, db_field.name)
					if instance and rel_instance:
						change_url = self.get_model_url(rel_model, 'change', rel_instance.pk)
						rel_change_url = self.get_model_url(self.model, 'change', instance.pk)
				if add_url or change_url:
					formfield.widget = RelatedFieldWidgetWrapper(
						formfield.widget,
						db_field.remote_field,
						add_url, rel_add_url,
						change_url, rel_change_url,
						request_params=self.request.GET.copy())
		return formfield


site.register_plugin(QuickFormPlugin, ModelFormAdminView)
site.register_plugin(QuickFormFormSetPlugin, ModelFormAdminView)
site.register_plugin(QuickAddBtnPlugin, ModelFormAdminView)
