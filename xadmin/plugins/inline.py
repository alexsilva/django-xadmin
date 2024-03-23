import copy
import inspect
from collections import OrderedDict

from crispy_forms.utils import TEMPLATE_PACK
from django import forms
from django.contrib.auth import get_permission_codename
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet, generic_inlineformset_factory
from django.forms.formsets import all_valid, DELETION_FIELD_NAME
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django.template import loader
from django.template.loader import render_to_string
from django.utils.encoding import smart_str
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

from xadmin.layout import FormHelper, Layout, flatatt, Container, Column, Field, Fieldset, LayoutObject
from xadmin.plugins.utils import get_context_dict
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ModelFormAdminView, DetailAdminView, filter_hook


class ShowField(Field):

	def __init__(self, admin_view, *args, **kwargs):
		super(ShowField, self).__init__(*args, **kwargs)
		self.admin_view = admin_view

	@property
	def field_template(self):
		template = "xadmin/layout/field_value.html"
		if self.admin_view.style == 'table':
			template = "xadmin/layout/field_value_td.html"
		return template

	def render(self, form, context, **kwargs):
		html = ''
		if hasattr(form, 'detail'):
			detail = form.detail
			context = get_context_dict(context)
			context['layout_field'] = self
			# When it allows inline add but can not change.
			show_hidden_detail = getattr(form, "show_hidden_detail", False)
			for field_name in self.fields:
				form_field = form.fields[field_name]
				form_field_widget = form_field.widget
				if not isinstance(form_field_widget, forms.HiddenInput):
					result = detail.get_field_result(field_name)
					context.update({'field': form[field_name], 'result': result})
					html += loader.render_to_string(self.field_template, context=context)
					# When it allows inline add but can not change.
					if show_hidden_detail:
						form_field.widget = forms.HiddenInput(attrs=form_field_widget.attrs)
						html += mark_safe(str(form[field_name]))
				elif show_hidden_detail:
					return super().render(form, context, **kwargs)
		return html


class DeleteField(Field):

	def render(self, form, context, **kwargs):
		if form.instance.pk:
			self.attrs['type'] = 'hidden'
			return super(DeleteField, self).render(form, context, **kwargs)
		else:
			return ""


class TDField(Field):
	template = "xadmin/layout/td-field.html"


class InlineStyleManager:
	inline_styles = {}

	def register_style(self, name, style):
		self.inline_styles[name] = style

	def get_style(self, name='stacked'):
		return self.inline_styles.get(name)


style_manager = InlineStyleManager()


class InlineStyle:
	template = 'xadmin/edit_inline/stacked.html'

	def __init__(self, view, formset):
		self.view = view
		self.formset = formset

	def get_formset_form(self, index):
		"""Returns form from index or empty form when extra == 0"""
		return (self.formset[index] if len(self.formset) else
		        self.formset.empty_form)

	def update_layout(self, helper):
		pass

	def get_attrs(self):
		return {}


style_manager.register_style('stacked', InlineStyle)


class OneInlineStyle(InlineStyle):
	template = 'xadmin/edit_inline/one.html'


style_manager.register_style("one", OneInlineStyle)


class AccInlineStyle(InlineStyle):
	template = 'xadmin/edit_inline/accordion.html'


style_manager.register_style("accordion", AccInlineStyle)


class TabInlineStyle(InlineStyle):
	template = 'xadmin/edit_inline/tab.html'


style_manager.register_style("tab", TabInlineStyle)


class TableInlineStyle(InlineStyle):
	template = 'xadmin/edit_inline/tabular.html'

	def update_layout(self, helper):
		form = self.get_formset_form(0)
		helper.add_layout(Layout(*[TDField(f) for f in form.fields.keys()]))

	def get_attrs(self):
		fields = []
		readonly_fields = []
		if len(self.formset):
			form = self.get_formset_form(0)
			fields = [f for k, f in form.fields.items() if k != DELETION_FIELD_NAME]
			readonly_fields = [f for f in getattr(form, 'readonly_fields', [])]
		return {
			'fields': fields,
			'readonly_fields': readonly_fields
		}


style_manager.register_style("table", TableInlineStyle)


def replace_field_to_value(layout, av):
	if layout:
		def is_nested(fields):
			"""Row(Column(Div(Col)))"""
			for field_name in fields:
				if not isinstance(field_name, str):
					return True
			return False

		for i, lo in enumerate(layout.fields):
			if isinstance(lo, DeleteField):
				continue
			elif isinstance(lo, Field) or issubclass(lo.__class__, Field):
				if is_nested(lo.fields):
					# bug fix: Row(Column(Div))
					replace_field_to_value(lo, av)
				else:
					layout.fields[i] = ShowField(av, *lo.fields, **lo.attrs)
			elif isinstance(lo, str):
				layout.fields[i] = ShowField(av, lo)
			elif hasattr(lo, 'get_field_names'):
				replace_field_to_value(lo, av)


class InlineFormSetMixin:
	"""InlineFormSet with permission check"""

	def __init__(self, *args, **kwargs):
		self.can_add = kwargs.pop('can_add', False)
		self.can_change = kwargs.pop('can_change', False)
		self.can_delete = kwargs.pop('can_delete', False)
		super().__init__(*args, **kwargs)

	def save_new(self, *args, **kwargs):
		kwargs['commit'] &= self.can_add
		return super().save_new(*args, **kwargs)

	def save_existing(self, *args, **kwargs):
		kwargs['commit'] &= self.can_change
		return super().save_existing(*args, **kwargs)

	def delete_existing(self, *args, **kwargs):
		kwargs['commit'] &= self.can_delete
		return super().delete_existing(*args, **kwargs)


class InlineModelAdmin(ModelFormAdminView):
	fk_name = None
	formset = BaseInlineFormSet
	extra = 3
	max_num = None
	can_delete = True
	fields = []
	admin_view = None
	horizontal_form_layout = False
	style = 'stacked'

	def init(self, admin_view):
		self.admin_view = admin_view
		self.parent_model = admin_view.model
		self.org_obj = getattr(admin_view, 'org_obj', None)
		self.model_instance = self.org_obj or admin_view.model()

		return self

	def get_formset_mixin(self):
		return type(f"{self.formset.__name__}PermsMixin", (InlineFormSetMixin, self.formset), {})

	@cached_property
	def has_inline_delete_permission(self):
		"""Whether inline is allowed to delete objects (depends on can_delete and model permission)"""
		return self.can_delete and self.has_delete_permission()

	@filter_hook
	def get_formset(self, **kwargs):
		"""Returns a BaseInlineFormSet class for use in admin add/change views."""
		if self.exclude is None:
			exclude = []
		else:
			exclude = list(self.exclude)
		exclude.extend(self.get_readonly_fields())
		if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
			# Take the custom ModelForm's Meta.exclude into account only if the
			# InlineModelAdmin doesn't define its own.
			exclude.extend(self.form._meta.exclude)
		# if exclude is an empty list we use None, since that's the actual
		# default
		exclude = exclude or None
		can_delete = self.has_inline_delete_permission
		formset = self.get_formset_mixin()
		defaults = {
			"form": self.form,
			"formset": formset,
			"fk_name": self.fk_name,
			'fields': self.fields if self.fields else forms.ALL_FIELDS,
			"exclude": exclude,
			"formfield_callback": self.formfield_for_dbfield,
			"extra": self.extra,
			"max_num": self.max_num,
			"can_delete": can_delete,
		}
		defaults.update(kwargs)

		return inlineformset_factory(self.parent_model, self.model, **defaults)

	@filter_hook
	def get_formset_attrs(self):
		"""Allows a plugin to change the options for creating a formset"""
		attrs = {
			'instance': self.model_instance,
			'queryset': self.queryset(),
			'can_add': self.has_add_permission(),
			'can_change': self.has_change_permission(),
			'can_delete': self.has_inline_delete_permission
		}
		if self.request_method == 'post':
			attrs.update({
				'data': self.request.POST, 'files': self.request.FILES,
				'save_as_new': "_saveasnew" in self.request.POST
			})
		return attrs

	@filter_hook
	def instance_form(self, **kwargs):
		formset = self.get_formset(**kwargs)
		formset_attrs = self.get_formset_attrs()
		instance = formset(**formset_attrs)
		instance.view = self

		helper = FormHelper()
		helper.form_tag = False
		helper.include_media = False
		helper.use_custom_control = False

		if self.horizontal_form_layout:
			helper.label_class = 'font-weight-bold col-sm-4 col-xl-3 border-left px-3 py-sm-2 pt-0 mb-0'
			helper.field_class = 'controls col-sm-8 col-xl-9 border-left px-3 py-sm-2 pt-0'
			helper.form_class = 'form-horizontal'
		else:
			helper.label_class = 'font-weight-bold col-12 border-left px-3 pt-0 pt-sm-2 mb-0'
			helper.field_class = 'controls col-12 border-left px-3 pt-0 pt-sm-2'

		# override form method to prevent render csrf_token in
		# inline forms, see template 'bootstrap/whole_uni_form.html'
		helper.form_method = 'get'

		style = style_manager.get_style('one' if self.max_num == 1 else self.style)(self, instance)
		style.name = self.style

		layout = copy.deepcopy(self.form_layout)

		# uses empty_form as a base to extract the fields and configure the layout
		# (even with extra==0 the layout has to work).
		empty_form = instance.empty_form

		def layout_hidden_fields(layout):
			rendered_fields = [p.name for p in layout.get_field_names()]
			layout.extend([f for f in empty_form.fields.keys() if f not in rendered_fields])

		if layout is None:
			layout = Layout(*empty_form.fields.keys())
		elif isinstance(layout, LayoutObject):
			layout = Layout(layout)
			layout_hidden_fields(layout)
		elif isinstance(layout, (list, tuple)) and len(layout) > 0:
			layout = Layout(*layout)
			layout_hidden_fields(layout)

		helper.add_layout(layout)
		style.update_layout(helper)

		# replace delete field with Dynamic field, for hidden delete field when instance is NEW.
		helper[DELETION_FIELD_NAME].wrap(DeleteField)

		instance.helper = helper
		instance.style = style

		readonly_fields = self.get_readonly_fields()
		if readonly_fields:
			for form in instance:
				form.readonly_fields = []
				try:
					# only a valid form can execute the save method
					form_instance = form.save(commit=False)
				except ValueError:
					form_instance = form.instance
				if form_instance:
					instance_fields = dict([(f.name, f) for f in form_instance._meta.get_fields()])
					for readonly_field in readonly_fields:
						value = None
						label = None
						if readonly_field in instance_fields:
							label = instance_fields[readonly_field].verbose_name
							value = smart_str(getattr(form_instance, readonly_field, None))
						elif inspect.ismethod(getattr(form_instance, readonly_field, None)):
							value = getattr(form_instance, readonly_field)()
							label = getattr(getattr(form_instance, readonly_field), 'short_description', readonly_field)
						elif inspect.ismethod(getattr(self, readonly_field, None)):
							value = getattr(self, readonly_field)(form_instance)
							label = getattr(getattr(self, readonly_field), 'short_description', readonly_field)
						if value:
							form.readonly_fields.append({'label': label, 'contents': value})
		return instance

	def has_auto_field(self, form):
		if form._meta.model._meta.has_auto_field:
			return True
		for parent in form._meta.model._meta.get_parent_list():
			if parent._meta.has_auto_field:
				return True
		return False

	def queryset(self):
		queryset = super(InlineModelAdmin, self).queryset()
		if not self.has_change_permission() and not self.has_view_permission():
			queryset = queryset.none()
		return queryset

	def has_add_permission(self, **kwargs):
		if self.opts.auto_created:
			return self.has_change_permission()

		codename = get_permission_codename('add', self.opts)
		return self.user.has_perm("%s.%s" % (self.opts.app_label, codename))

	def has_change_permission(self, **kwargs):
		opts = self.opts
		if opts.auto_created:
			for field in opts.fields:
				if field.remote_field and field.remote_field.model != self.parent_model:
					opts = field.remote_field.model._meta
					break

		codename = get_permission_codename('change', opts)
		return self.user.has_perm("%s.%s" % (opts.app_label, codename))

	def has_delete_permission(self, **kwargs):
		if self.opts.auto_created:
			return self.has_change_permission()

		codename = get_permission_codename('delete', self.opts)
		return self.user.has_perm("%s.%s" % (self.opts.app_label, codename))


class GenericInlineModelAdmin(InlineModelAdmin):
	ct_field = "content_type"
	ct_fk_field = "object_id"

	formset = BaseGenericInlineFormSet

	@filter_hook
	def get_formset(self, **kwargs):
		if self.exclude is None:
			exclude = []
		else:
			exclude = list(self.exclude)
		exclude.extend(self.get_readonly_fields())
		if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
			# Take the custom ModelForm's Meta.exclude into account only if the
			# GenericInlineModelAdmin doesn't define its own.
			exclude.extend(self.form._meta.exclude)
		exclude = exclude or None
		can_delete = self.has_inline_delete_permission
		formset = self.get_formset_mixin()
		defaults = {
			"ct_field": self.ct_field,
			"fk_field": self.ct_fk_field,
			"form": self.form,
			"formfield_callback": self.formfield_for_dbfield,
			"formset": formset,
			"extra": self.extra,
			"can_delete": can_delete,
			"can_order": False,
			"max_num": self.max_num,
			"exclude": exclude,
			'fields': forms.ALL_FIELDS
		}
		defaults.update(kwargs)

		return generic_inlineformset_factory(self.model, **defaults)


class InlineFormset(Fieldset):

	def __init__(self, formset, allow_blank=False, **kwargs):
		self.fields = []
		self.css_class = kwargs.pop('css_class', '')
		self.css_id = "%s-group" % formset.prefix
		self.template = formset.style.template
		self.inline_style = formset.style.name
		if allow_blank and len(formset) == 0:
			self.template = 'xadmin/edit_inline/blank.html'
			self.inline_style = 'blank'
		self.formset = formset
		self.model = formset.model
		self.opts = formset.model._meta
		self.flat_attrs = flatatt(kwargs)
		self.extra_attrs = formset.style.get_attrs()

	def render(self, form, context, **kwargs):
		context = get_context_dict(context)
		context.update(dict(
			formset=self,
			prefix=self.formset.prefix,
			inline_style=self.inline_style,
			**self.extra_attrs
		))
		return render_to_string(self.template, context)


class Inline(Fieldset):

	def __init__(self, rel_model):
		self.model = rel_model
		self.fields = []
		super(Inline, self).__init__(legend="")

	def render(self, form, context, **kwargs):
		return ""


def get_first_field(layout, clz):
	for layout_object in layout.fields:
		if issubclass(layout_object.__class__, clz):
			return layout_object
		elif hasattr(layout_object, 'get_field_names'):
			gf = get_first_field(layout_object, clz)
			if gf:
				return gf


def replace_inline_objects(layout, fs):
	if not fs:
		return
	for i, layout_object in enumerate(layout.fields):
		if isinstance(layout_object, Inline) and layout_object.model in fs:
			layout.fields[i] = fs.pop(layout_object.model)
		elif hasattr(layout_object, 'get_field_names'):
			replace_inline_objects(layout_object, fs)


class InlineFormsetPlugin(BaseAdminPlugin):
	inlines = []

	def init_request(self, *args, **kwargs):
		return not isinstance(self.admin_view, InlineModelAdmin)

	@cached_property
	def inline_instances(self):
		inline_instances = []
		for inline_class in self.inlines:
			inline = self.admin_view.get_view((getattr(inline_class, 'generic_inline', False) and
			                                   GenericInlineModelAdmin or InlineModelAdmin),
			                                  inline_class).init(self.admin_view)
			if not (inline.has_add_permission() or
			        inline.has_change_permission() or
			        inline.has_delete_permission() or
			        inline.has_view_permission()):
				continue
			if not inline.has_add_permission():
				inline.max_num = 0
			inline_instances.append(inline)
		return inline_instances

	def instance_forms(self, ret):
		self.formsets = []
		for inline in self.inline_instances:
			if inline.has_change_permission():
				self.formsets.append(inline.instance_form())
			else:
				self.formsets.append(self._get_detail_formset_instance(inline))
		self.admin_view.formsets = self.formsets

	def valid_forms(self, result):
		bounded = (f.is_bound for f in self.formsets)
		if any(bounded):
			result &= all_valid(self.formsets)
		return result

	def save_related(self):
		new_obj = getattr(self.admin_view, "new_obj", None)
		if new_obj is None:
			return
		for formset in self.formsets:
			formset.instance = new_obj
			formset.save()

	def get_context(self, context):
		context['inline_formsets'] = self.formsets
		return context

	def get_error_list(self, errors):
		for fs in self.formsets:
			errors.extend(fs.non_form_errors())
			for errors_in_inline_form in fs.errors:
				errors.extend(errors_in_inline_form.values())
		return errors

	def get_form_layout(self, layout):
		allow_blank = isinstance(self.admin_view, DetailAdminView)
		# fixed #176, #363 bugs, change dict to list
		fs = OrderedDict([(f.model, InlineFormset(f, allow_blank)) for f in self.formsets])
		replace_inline_objects(layout, fs)

		if fs:
			container = get_first_field(layout, Column)
			if not container:
				container = get_first_field(layout, Container)
			if not container:
				container = layout

			# fixed #176, #363 bugs, change dict to list
			for key, value in fs.items():
				container.append(value)

		return layout

	def get_media(self, media):
		for fs in self.formsets:
			media += fs.view.get_media()
			media += fs.media
		if self.formsets:
			media += self.vendor('xadmin.plugin.formset.js',
			                     'xadmin.plugin.formset.css')
		return media

	def _get_detail_formset_instance(self, inline):
		detail_page = isinstance(self.admin_view, DetailAdminView)
		formset = inline.instance_form(extra=0 if detail_page else inline.extra,
		                               max_num=0 if detail_page else inline.max_num,
		                               can_delete=False if detail_page else inline.has_delete_permission())
		formset.detail_page = detail_page
		if formset.helper.layout:
			replace_field_to_value(formset.helper.layout, inline)
			model = inline.model
			opts = model._meta
			option_class = type(f"{opts.app_label}{opts.model_name}AdminMixin",
			                    (getattr(inline, "detail_options", object),),
			                    {"model": model})
			for form in formset.forms:
				instance = form.instance
				if instance.pk:
					form.detail = self.get_view(DetailAdminUtil, option_class, instance)
					form.show_hidden_detail = not formset.detail_page
		return formset


class DetailAdminUtil(DetailAdminView):

	def init_request(self, obj, *args, **kwargs):
		self.obj = obj
		self.org_obj = obj


class DetailInlineFormsetPlugin(InlineFormsetPlugin):

	def get_model_form(self, form, **kwargs):
		self.formsets = [self._get_detail_formset_instance(
			inline) for inline in self.inline_instances]
		return form


site.register_plugin(InlineFormsetPlugin, ModelFormAdminView)
site.register_plugin(DetailInlineFormsetPlugin, DetailAdminView)
