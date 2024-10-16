import copy
import re

from crispy_forms.utils import TEMPLATE_PACK
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.forms.models import modelform_factory, modelform_defines_fields
from django.forms.widgets import Media
from django.http import Http404, HttpResponseRedirect
from django.template import loader
from django.template.response import TemplateResponse
from django.utils.encoding import force_str
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import get_text_list
from django.utils.translation import gettext as _
from django.core.exceptions import FieldDoesNotExist

from xadmin import widgets
from xadmin.layout import FormHelper, Layout, Fieldset, TabHolder, Container, Column, Col, Field, Tab
from xadmin.util import unquote
from xadmin.views.base import ModelAdminView, filter_hook, csrf_protect_m
from xadmin.views.detail import DetailAdminUtil

FORMFIELD_FOR_DBFIELD_DEFAULTS = {
	models.DateTimeField: {
		'form_class': forms.SplitDateTimeField,
		'widget': widgets.AdminSplitDateTime
	},
	models.DateField: {'widget': widgets.AdminDateWidget},
	models.TimeField: {'widget': widgets.AdminTimeWidget},
	models.TextField: {'widget': widgets.AdminTextareaWidget},
	models.URLField: {'widget': widgets.AdminURLFieldWidget},
	models.IntegerField: {'widget': widgets.AdminIntegerFieldWidget},
	models.BigIntegerField: {'widget': widgets.AdminIntegerFieldWidget},
	models.CharField: {'widget': widgets.AdminTextInputWidget},
	models.IPAddressField: {'widget': widgets.AdminTextInputWidget},
	models.ImageField: {'widget': widgets.AdminFileWidget},
	models.FileField: {'widget': widgets.AdminFileWidget},
	models.ForeignKey: {'widget': widgets.AdminSelectWidget},
	models.OneToOneField: {'widget': widgets.AdminSelectWidget},
	models.ManyToManyField: {'widget': widgets.AdminSelectMultiple},
}


class ReadOnlyField(Field):
	template = "xadmin/layout/field_value_form.html"

	def __init__(self, *args, **kwargs):
		self.detail = kwargs.pop('detail')
		super(ReadOnlyField, self).__init__(*args, **kwargs)

	def render(self, form, context, **kwargs):
		html = ''
		for field in self.fields:
			if isinstance(field, type(self)):
				html += field.render(self, context, **kwargs)
			else:
				result = self.detail.get_field_result(field)
				field = {'auto_id': field}
				html += loader.render_to_string(
					self.template, {'field': field, 'result': result})
		return html


class ModelFormAdminView(ModelAdminView):
	form = forms.ModelForm
	formfield_overrides = {}
	formfield_widgets = {}
	readonly_fields = ()
	form_inlines = ()
	style_fields = {}
	exclude = None
	relfield_style = None

	save_as = False
	save_on_top = False

	add_form_template = None
	change_form_template = None

	# If enabled, it allows adding the inline label to the input.
	horizontal_form_layout = False
	form_layout = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		overrides = FORMFIELD_FOR_DBFIELD_DEFAULTS.copy()
		overrides.update(self.formfield_overrides)
		self.formfield_overrides = overrides

	@filter_hook
	def get_form_inlines(self) -> list:
		"""Allows additional inline configuration"""
		return list(self.form_inlines)

	@filter_hook
	def formfield_for_dbfield(self, db_field, **kwargs):
		# If it uses an intermediary model that isn't auto created, don't show
		# a field in admin.
		if isinstance(db_field, models.ManyToManyField) and not db_field.remote_field.through._meta.auto_created:
			return None

		attrs = self.get_field_attrs(db_field, **kwargs)
		return db_field.formfield(**dict(attrs, **kwargs))

	@filter_hook
	def get_field_style(self, db_field, style, **kwargs):
		if style in ('radio', 'radio-inline') and (db_field.choices or isinstance(db_field, models.ForeignKey)):
			attrs = {'widget': widgets.AdminRadioSelect(
				attrs={'inline': 'inline' if style == 'radio-inline' else ''})}
			if db_field.choices:
				attrs['choices'] = db_field.get_choices(
					include_blank=db_field.blank,
					blank_choice=[('', _('Null'))]
				)
			return attrs

		if style in ('checkbox', 'checkbox-inline') and isinstance(db_field, models.ManyToManyField):
			return {'widget': widgets.AdminCheckboxSelect(attrs={'inline': style == 'checkbox-inline'}),
			        'help_text': None}

	@filter_hook
	def get_field_attrs(self, db_field, **kwargs):

		if db_field.name in self.style_fields:
			attrs = self.get_field_style(db_field, self.style_fields[db_field.name], **kwargs)
			if attrs:
				return attrs

		if hasattr(db_field, "remote_field") and db_field.remote_field:
			related_modeladmin = self.admin_site._registry.get(db_field.remote_field.model)
			if related_modeladmin and hasattr(related_modeladmin, 'relfield_style'):
				attrs = self.get_field_style(
					db_field, related_modeladmin.relfield_style, **kwargs)
				if attrs:
					return attrs

		if db_field.choices:
			return {'widget': widgets.AdminSelectWidget}

		for klass in db_field.__class__.mro():
			if klass in self.formfield_overrides:
				return self.formfield_overrides[klass].copy()

		return {}

	@filter_hook
	def prepare_form(self):
		self.model_form = self.get_model_form()

	@filter_hook
	def instance_forms(self):
		self.form_obj = self.model_form(**self.get_form_datas())

	def setup_forms(self):
		helper = self.get_form_helper()
		if helper:
			self.form_obj.helper = helper

	@filter_hook
	def valid_forms(self):
		return self.form_obj.is_valid()

	@filter_hook
	def get_model_form(self, **kwargs):
		"""
		Returns a Form class for use in the admin add view. This is used by
		add_view and change_view.
		"""
		form = self.get_form_class()
		form_opts = getattr(form, "_meta", None)
		fields = self.get_form_fields()
		fields_exclude = self.get_form_exclude()
		exclude = [] if fields_exclude is None else list(fields_exclude)
		exclude.extend(self.get_readonly_fields())
		form_widgets = self.formfield_widgets
		if form_opts:
			if fields_exclude is None and form_opts.exclude:
				# Take the custom ModelForm's Meta.exclude into account only if the
				# ModelAdmin doesn't define its own.
				exclude.extend(form_opts.exclude)
			if form_opts.widgets:
				form_widgets = form_opts.widgets.copy()
				form_widgets.update(self.formfield_widgets)
		defaults = {
			"form": form,
			"fields": fields and list(fields) or None,
			# if exclude is an empty list we pass None to be consistent with the
			# default on modelform_factory
			"exclude": exclude or None,
			"formfield_callback": self.formfield_for_dbfield,
			"widgets": form_widgets
		}
		defaults.update(kwargs)

		if defaults['fields'] is None and not modelform_defines_fields(defaults['form']):
			defaults['fields'] = forms.ALL_FIELDS

		return modelform_factory(self.model, **defaults)

	@filter_hook
	def get_full_layout(self, fields, **options):
		"""Default layout for when one has not been defined"""
		return Layout(Container(Col('full', Fieldset("", *fields, **options),
		                            horizontal=True, span=12)))

	@filter_hook
	def get_form_layout(self):
		layout = copy.deepcopy(self.form_layout)
		fields = list(self.form_obj.fields.keys()) + list(self.get_readonly_fields())
		if layout is None:
			layout = self.get_full_layout(fields, css_class="unsort no_title")
		elif type(layout) in (list, tuple) and len(layout) > 0:
			if isinstance(layout[0], Column):
				fs = layout
			elif isinstance(layout[0], (Fieldset, TabHolder)):
				fs = (Col('full', *layout, horizontal=True, span=12),)
			else:
				fs = (Col('full', Fieldset("", *layout, css_class="unsort no_title"), horizontal=True, span=12),)

			layout = Layout(Container(*fs))

			rendered_fields = [p.name for p in layout.get_field_names()]
			container = layout[0].fields
			other_fieldset = Fieldset(_('Other Fields'), *[f for f in fields if f not in rendered_fields])

			if len(other_fieldset.fields):
				if len(container) and isinstance(container[0].fields[0], TabHolder):

					other_fieldset.css_class = 'unsort no_title'
					container[0].fields[0].append(Tab(_('Other Fields'), other_fieldset))

				elif len(container) and isinstance(container[0], Column):
					container[0].fields.append(other_fieldset)
				else:
					container.append(other_fieldset)

		return layout

	@filter_hook
	def get_form_helper(self):
		helper = FormHelper()
		helper.disable_csrf = True
		helper.form_tag = False
		helper.html5_required = True
		helper.label_class = 'font-weight-bold'

		# Lets you add the inline label to the input.
		if self.horizontal_form_layout:
			helper.form_class = 'form-horizontal'
			helper.field_class = 'controls col-sm-8'
			helper.label_class = 'col-sm-4'
		else:
			helper.field_class = 'controls'

		helper.include_media = False
		helper.use_custom_control = False
		helper.add_layout(self.get_form_layout())

		# deal with readonly fields
		readonly_fields = self.get_readonly_fields()
		if readonly_fields:
			detail = self.get_model_view(DetailAdminUtil, self.model,
			                             self.form_obj.instance,
			                             form_obj=self.form_obj)
			for field in readonly_fields:
				helper[field].wrap(ReadOnlyField, detail=detail)

		return helper

	@filter_hook
	def get_form_class(self):
		return self.form

	@filter_hook
	def get_form_exclude(self):
		return self.exclude

	@filter_hook
	def get_form_fields(self):
		return self.fields

	@filter_hook
	def get_readonly_fields(self):
		"""
		Hook for specifying custom readonly fields.
		"""
		return self.readonly_fields

	@filter_hook
	def save_forms(self):
		self.new_obj = self.form_obj.save(commit=False)

	@filter_hook
	def change_message(self):
		change_message = []
		if self.org_obj is None:
			change_message.append(_('Added.'))
		elif self.form_obj.changed_data:
			change_message.append(_('Changed %s.') % get_text_list(self.form_obj.changed_data, _('and')))

		change_message = ' '.join(change_message)
		return change_message or _('No fields changed.')

	@filter_hook
	def save_models(self):
		self.new_obj.save()
		flag = self.org_obj is None and 'create' or 'change'
		self.log(flag, self.change_message(), self.new_obj)

	@filter_hook
	def save_related(self):
		self.form_obj.save_m2m()

	@csrf_protect_m
	@filter_hook
	def get(self, request, *args, **kwargs):
		self.instance_forms()
		self.setup_forms()

		return self.get_response()

	@csrf_protect_m
	@transaction.atomic
	@filter_hook
	def post(self, request, *args, **kwargs):
		self.instance_forms()
		self.setup_forms()

		if self.valid_forms():
			self.save_forms()
			self.save_models()
			self.save_related()
			response = self.post_response()
			if isinstance(response, str):
				return HttpResponseRedirect(response)
			else:
				return response
		else:
			return self.get_response()

	@filter_hook
	def get_context(self):
		add = self.org_obj is None
		change = self.org_obj is not None

		new_context = {
			'form': self.form_obj,
			'original': self.org_obj,
			'show_delete': self.org_obj is not None,
			'add': add,
			'change': change,
			'errors': self.get_error_list(),

			'has_add_permission': self.has_add_permission(),
			'has_view_permission': self.has_view_permission(),
			'has_change_permission': self.has_change_permission(self.org_obj),
			'has_delete_permission': self.has_delete_permission(self.org_obj),

			'has_file_field': True,  # FIXME - this should check if form or formsets have a FileField,
			'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
			'form_url': '',
			'content_type_id': ContentType.objects.get_for_model(self.model).id,
			'save_as': self.save_as,
			'save_on_top': self.save_on_top,
		}

		# for submit line
		new_context.update({
			'onclick_attrib': '',
			'show_delete_link': (new_context['has_delete_permission']
			                     and (change or new_context['show_delete'])),
			'show_save_as_new': change and self.save_as,
			'show_save_and_add_another': new_context['has_add_permission'] and
			                             (not self.save_as or add),
			'show_save_and_continue': new_context['has_change_permission'],
			'show_save': True
		})

		if self.org_obj and new_context['show_delete_link']:
			new_context['delete_url'] = self.model_admin_url(
				'delete', self.org_obj.pk)

		context = super(ModelFormAdminView, self).get_context()
		context.update(new_context)
		return context

	@filter_hook
	def get_error_list(self):
		errors = forms.utils.ErrorList()
		if self.form_obj.is_bound:
			errors.extend(self.form_obj.errors.values())
		return errors

	@filter_hook
	def get_media(self):
		try:
			m = self.form_obj.media
		except:
			m = Media()
		return super(ModelFormAdminView, self).get_media() + m + \
		       self.vendor('xadmin.page.form.js', 'xadmin.form.css')


class CreateAdminView(ModelFormAdminView):

	def init_request(self, *args, **kwargs):
		self.org_obj = None

		if not self.has_add_permission():
			raise PermissionDenied

		# comm method for both get and post
		self.prepare_form()

	@filter_hook
	def get_form_datas(self):
		# Prepare the dict of initial data from the request.
		# We have to special-case M2Ms as a list of comma-separated PKs.
		if self.request_method == 'get':
			initial = dict(self.request.GET.items())
			initial_new = {}
			for key in initial:
				key_prefix = key
				if self.model_form.prefix:
					key = re.sub('^' + re.escape(self.model_form.prefix + '-'), '', key)
				try:
					field = self.opts.get_field(key)
				except FieldDoesNotExist:
					continue
				if isinstance(field, models.ManyToManyField):
					initial_new[key] = initial[key_prefix].split(",")
				else:
					# field value without a prefix
					initial_new[key] = initial[key_prefix]
			initial.update(initial_new)
			return {'initial': initial}
		else:
			return {'data': self.request.POST, 'files': self.request.FILES}

	@filter_hook
	def get_context(self):
		new_context = {
			'title': _('Add %s') % force_str(self.opts.verbose_name),
		}
		context = super(CreateAdminView, self).get_context()
		context.update(new_context)
		return context

	@filter_hook
	def get_breadcrumb(self):
		bcs = super(ModelFormAdminView, self).get_breadcrumb()
		item = {'title': _('Add %s') % force_str(self.opts.verbose_name)}
		if self.has_add_permission():
			item['url'] = self.model_admin_url('add')
		bcs.append(item)
		return bcs

	@filter_hook
	def get_response(self):
		context = self.get_context()
		context.update(self.kwargs or {})

		return TemplateResponse(
			self.request, self.add_form_template or self.get_template_list(
				'views/model_form.html'),
			context)

	@filter_hook
	def post_response(self):
		"""
		Determines the HttpResponse for the add_view stage.
		"""
		request = self.request

		msg = _('The %(name)s "%(obj)s" was added successfully.') % {
			'name': escape(force_str(self.opts.verbose_name)),
			'obj': "<a class='alert-link' href='%s'>%s</a>" % (
				self.model_admin_url('change', self.new_obj._get_pk_val()),
				escape(force_str(self.new_obj))
			)
		}

		if "_continue" in request.POST:
			if self.has_change_permission(self.new_obj):
				self.message_user(mark_safe(msg + ' ' + _("You may edit it again below.")), 'success')
				return self.model_admin_url('change', self.new_obj._get_pk_val())
			else:
				# when the user cannot continue editing, they will only see the details screen.
				return self.model_admin_url("detail", self.new_obj.pk)
		if "_addanother" in request.POST:
			self.message_user(mark_safe(msg + ' ' + (_("You may add another %s below.") %
			                                         escape(force_str(self.opts.verbose_name)))),
			                  'success')
			return request.path
		else:
			self.message_user(mark_safe(msg), 'success')

			# Figure out where to redirect. If the user has change permission,
			# redirect to the change-list page for this object. Otherwise,
			# redirect to the admin index.
			if "_redirect" in request.POST:
				return request.POST["_redirect"]
			elif "_redirect" in request.GET:  # redirect from dashboard
				return request.GET["_redirect"]
			elif self.has_view_permission():
				return self.model_admin_url('changelist')
			else:
				return self.get_admin_url('index')


class UpdateAdminView(ModelFormAdminView):

	def init_request(self, object_id, *args, **kwargs):
		self.org_obj = self.get_object(unquote(object_id))

		if not self.has_change_permission(self.org_obj):
			raise PermissionDenied

		if self.org_obj is None:
			raise Http404(_('%(name)s object with primary key %(key)r does not exist.') %
			              {'name': force_str(self.opts.verbose_name), 'key': escape(object_id)})

		# comm method for both get and post
		self.prepare_form()

	@filter_hook
	def get_form_datas(self):
		params = {'instance': self.org_obj}
		if self.request_method == 'post':
			params.update({'data': self.request.POST, 'files': self.request.FILES})
		return params

	@filter_hook
	def get_context(self):
		new_context = {
			'title': _('Change %s') % force_str(self.org_obj),
			'object_id': str(self.org_obj.pk),
		}
		context = super(UpdateAdminView, self).get_context()
		context.update(new_context)
		return context

	def block_extrahead(self, context, nodes):
		nodes.append(f"""
        <script type="text/javascript">
        window.xadmin.object_id = "{context['object_id']}";
        </script>
         """)

	@filter_hook
	def get_breadcrumb(self):
		bcs = super(ModelFormAdminView, self).get_breadcrumb()

		item = {'title': force_str(self.org_obj)}
		if self.has_change_permission():
			item['url'] = self.model_admin_url('change', self.org_obj.pk)
		bcs.append(item)

		return bcs

	@filter_hook
	def get_response(self, *args, **kwargs):
		context = self.get_context()
		context.update(kwargs or {})

		return TemplateResponse(
			self.request, self.change_form_template or self.get_template_list(
				'views/model_form.html'),
			context)

	def post(self, request, *args, **kwargs):
		if "_saveasnew" in self.request.POST:
			return self.get_model_view(CreateAdminView, self.model).post(request)
		return super(UpdateAdminView, self).post(request, *args, **kwargs)

	@filter_hook
	def post_response(self):
		"""
		Determines the HttpResponse for the change_view stage.
		"""
		opts = self.new_obj._meta
		obj = self.new_obj
		request = self.request
		verbose_name = opts.verbose_name

		pk_value = obj._get_pk_val()

		msg = _('The %(name)s "%(obj)s" was changed successfully.') % {
			'name': force_str(verbose_name),
			'obj': force_str(obj)
		}
		if "_continue" in request.POST:
			if self.has_change_permission(obj):
				self.message_user(msg + ' ' + _("You may edit it again below."), 'success')
				return request.path
			else:
				# when the user cannot continue editing, they will only see the details screen.
				return self.model_admin_url("detail", obj.pk)
		elif "_addanother" in request.POST:
			self.message_user(msg + ' ' + (_("You may add another %s below.")
			                               % force_str(verbose_name)), 'success')
			return self.model_admin_url('add')
		else:
			self.message_user(msg, 'success')
			# Figure out where to redirect. If the user has change permission,
			# redirect to the change-list page for this object. Otherwise,
			# redirect to the admin index.
			if "_redirect" in request.POST:
				return request.POST["_redirect"]
			elif self.has_view_permission():
				change_list_url = self.model_admin_url('changelist')
				if 'LIST_QUERY' in self.request.session and self.request.session['LIST_QUERY'][0] == self.model_info:
					change_list_url += '?' + self.request.session['LIST_QUERY'][1]
				return change_list_url
			else:
				return self.get_admin_url('index')


class ModelFormAdminUtil(ModelFormAdminView):

	def init_request(self, obj=None):
		self.org_obj = obj
		self.prepare_form()
		self.instance_forms()

	@filter_hook
	def get_form_datas(self):
		return {'instance': self.org_obj}
