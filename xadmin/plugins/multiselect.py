# coding:utf-8

from django import forms
from django.db.models import ManyToManyField
from django.forms.utils import flatatt
from django.utils.encoding import force_str
from django.utils.html import escape, conditional_escape

import xadmin
from xadmin.util import vendor
from xadmin.views import BaseAdminPlugin, ModelFormAdminView


class SelectMultipleTransfer(forms.SelectMultiple):
	template_name = 'xadmin/forms/transfer.html'

	def __init__(self, attrs=None, choices=(), verbose_name=None, is_stacked=False):
		self.verbose_name = verbose_name
		self.is_stacked = is_stacked
		super(SelectMultipleTransfer, self).__init__(attrs, choices)

	def render_opt(self, selected_choices, option_value, option_label):
		option_value = force_str(option_value)
		return '<option value="%s">%s</option>' % (
			escape(option_value), conditional_escape(force_str(option_label))), bool(option_value in selected_choices)

	def get_context(self, name, value, attrs):
		ctx = super(SelectMultipleTransfer, self).get_context(name, value, attrs)
		if attrs is None:
			attrs = {}
		attrs['class'] = ''
		if self.is_stacked:
			attrs['class'] += 'stacked'
		if value is None:
			value = []
		final_attrs = self.build_attrs(attrs, extra_attrs={'name': name})

		selected_choices = set(force_str(v) for v in value)
		available_output = []
		chosen_output = []

		for option_value, option_label in self.choices:
			if isinstance(option_label, (list, tuple)):
				available_output.append('<optgroup label="%s">' %
				                        escape(force_str(option_value)))
				for option in option_label:
					output, selected = self.render_opt(
						selected_choices, *option)
					if selected:
						chosen_output.append(output)
					else:
						available_output.append(output)
				available_output.append('</optgroup>')
			else:
				output, selected = self.render_opt(
					selected_choices, option_value, option_label)
				if selected:
					chosen_output.append(output)
				else:
					available_output.append(output)

		context = {
			'verbose_name': self.verbose_name,
			'attrs': attrs,
			'field_id': attrs['id'],
			'flatatts': flatatt(final_attrs),
			'available_options': '\n'.join(available_output),
			'chosen_options': '\n'.join(chosen_output),
		}

		ctx.update(context)
		return ctx

	@property
	def media(self):
		return vendor('xadmin.widget.select-transfer.js', 'xadmin.widget.select-transfer.css')


class SelectMultipleDropdown(forms.SelectMultiple):

	@property
	def media(self):
		return vendor('multiselect.js', 'multiselect.css', 'xadmin.widget.multiselect.js')

	def render(self, name, value, attrs=None, choices=(), **kwargs):
		if attrs is None:
			attrs = {}
		attrs['class'] = 'selectmultiple selectdropdown'
		return super(SelectMultipleDropdown, self).render(name, value, attrs, choices)


class M2MSelectPlugin(BaseAdminPlugin):

	def init_request(self, *args, **kwargs):
		return hasattr(self.admin_view, 'style_fields') and \
		       (
				       'm2m_transfer' in self.admin_view.style_fields.values() or
				       'm2m_dropdown' in self.admin_view.style_fields.values()
		       )

	def get_field_style(self, attrs, db_field, style, **kwargs):
		if style == 'm2m_transfer' and isinstance(db_field, ManyToManyField):
			return {'widget': SelectMultipleTransfer(verbose_name=db_field.verbose_name,
			                                         is_stacked=False), 'help_text': ''}
		if style == 'm2m_dropdown' and isinstance(db_field, ManyToManyField):
			return {'widget': SelectMultipleDropdown, 'help_text': ''}
		return attrs


xadmin.site.register_plugin(M2MSelectPlugin, ModelFormAdminView)
