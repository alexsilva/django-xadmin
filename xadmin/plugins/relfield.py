from django import forms
from django.db import models
from django.utils.html import escape, format_html
from django.utils.text import Truncator
from django.utils.translation import gettext as _

from xadmin.sites import site
from xadmin.util import vendor, get_limit_choices_to_url_params
from xadmin.views import BaseAdminPlugin, ModelFormAdminView


class ForeignKeySearchWidget(forms.Widget):
	template_name = "xadmin/plugins/widgets/foreignkey_search_select.html"

	def __init__(self, rel, admin_view, attrs=None, using=None):
		self.rel = rel
		self.admin_view = admin_view
		self.db = using
		super(ForeignKeySearchWidget, self).__init__(attrs)

	def build_attrs(self, base_attrs=None, extra_attrs=None, **kwargs):
		if base_attrs is None:
			base_attrs = {}
		to_opts = self.rel.model._meta
		if "class" not in base_attrs:
			base_attrs['class'] = 'select-search'
		else:
			base_attrs['class'] = base_attrs['class'] + ' select-search'
		base_attrs['data-search-url'] = self.admin_view.get_admin_url(
			'%s_%s_changelist' % (to_opts.app_label, to_opts.model_name))
		base_attrs['data-placeholder'] = _('Search %s') % to_opts.verbose_name
		base_attrs['data-choices'] = '?'
		rel_limit_choices_to = get_limit_choices_to_url_params(self.rel)
		if rel_limit_choices_to:
			for key in rel_limit_choices_to:
				base_attrs['data-choices'] += "&_p_%s=%s" % (key, rel_limit_choices_to[key])
			base_attrs['data-choices'] = format_html(base_attrs['data-choices'])
		base_attrs.update(kwargs)
		return super(ForeignKeySearchWidget, self).build_attrs(base_attrs, extra_attrs=extra_attrs)

	def get_context(self, name, value, attrs):
		context = super(ForeignKeySearchWidget, self).get_context(name, value, attrs)
		if value:
			context['widget']['value_label'] = self.label_for_value(value)
		return context

	def label_for_value(self, value):
		key = self.rel.get_related_field().name
		model = self.rel.model
		try:
			obj = model._default_manager.using(self.db).get(**{key: value})
			return '%s' % escape(Truncator(obj).words(14, truncate='...'))
		except (ValueError, model.DoesNotExist):
			return ""

	@property
	def media(self):
		return vendor('select.js', 'select.css', 'xadmin.widget.select.js')


class ForeignKeySelectWidget(ForeignKeySearchWidget):

	def build_attrs(self, base_attrs=None, **kwargs):
		if base_attrs is None:
			base_attrs = {}
		attrs = super(ForeignKeySelectWidget, self).build_attrs(base_attrs, **kwargs)
		if "class" not in attrs:
			attrs['class'] = 'select-preload'
		else:
			attrs['class'] = attrs['class'] + ' select-preload'
		attrs['data-placeholder'] = _('Select %s') % self.rel.model._meta.verbose_name
		return attrs


class RelateFieldPlugin(BaseAdminPlugin):
	related_limit_choices_distinct = ()

	def get_field_style(self, attrs, db_field, style, **kwargs):
		# search able fk field
		if style in ('fk-ajax', 'fk-select') and isinstance(db_field, models.ForeignKey):
			if (db_field.remote_field.model in self.admin_view.admin_site._registry) and \
					self.has_model_perm(db_field.remote_field.model, 'view'):
				db = kwargs.get('using')
				widget = (style == 'fk-ajax' and ForeignKeySearchWidget or ForeignKeySelectWidget)
				return dict(attrs or {}, widget=widget(db_field.remote_field, self.admin_view, using=db))
		return attrs

	def formfield_for_dbfield(self, formfield, db_field, **kwargs):
		if (isinstance(db_field, (models.ForeignKey, models.ManyToManyField)) and
				getattr(db_field.remote_field, "limit_choices_to", None) and
				(db_field.name in self.related_limit_choices_distinct or
				 type(db_field) in self.related_limit_choices_distinct)):
			# in form validation this avoids duplicates in the results
			formfield.queryset = formfield.queryset.distinct()
		return formfield


site.register_plugin(RelateFieldPlugin, ModelFormAdminView)
