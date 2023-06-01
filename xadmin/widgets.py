"""
Form Widget classes specific to the Django admin site.
"""
import re
from itertools import chain

from django import forms
from django.forms.widgets import ChoiceWidget as RadioChoiceInput
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from xadmin.util import vendor


class AdminDateWidget(forms.DateInput):

	@property
	def media(self):
		return vendor('datepicker.js', 'datepicker.css', 'xadmin.widget.datetime.js')

	def __init__(self, attrs=None, format=None):
		final_attrs = {'class': 'date-field form-control', 'size': '10', 'autocomplete': 'off'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminDateWidget, self).__init__(attrs=final_attrs, format=format)

	def render(self, name, value, attrs=None, **kwargs):
		input_html = super(AdminDateWidget, self).render(name, value, attrs, **kwargs)
		return mark_safe(render_to_string('xadmin/widgets/date.html', context={'date_input_html': input_html}))


class AdminTimeWidget(forms.TimeInput):

	@property
	def media(self):
		return vendor('datepicker.js', 'clockpicker.js', 'clockpicker.css', 'xadmin.widget.datetime.js')

	def __init__(self, attrs=None, format=None):
		final_attrs = {'class': 'time-field form-control', 'size': '8', 'autocomplete': 'off'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminTimeWidget, self).__init__(attrs=final_attrs, format=format)

	def render(self, name, value, attrs=None, **kwargs):
		input_html = super(AdminTimeWidget, self).render(name, value, attrs, **kwargs)
		return mark_safe(render_to_string("xadmin/widgets/time.html", context={'time_input_html': input_html}))


class AdminSelectWidget(forms.Select):

	@property
	def media(self):
		return vendor('select.js', 'select.css', 'xadmin.widget.select.js')


class AdminSplitDateTime(forms.SplitDateTimeWidget):
	"""
	A SplitDateTime Widget that has some admin-specific styling.
	"""

	def __init__(self, attrs=None):
		widgets = [AdminDateWidget, AdminTimeWidget]
		# Note that we're calling MultiWidget, not SplitDateTimeWidget, because
		# we want to define widgets.
		final_attrs = {'autocomplete': 'off'}
		if attrs is not None:
			final_attrs.update(attrs)
		forms.MultiWidget.__init__(self, widgets, attrs=final_attrs)

	def render(self, name, value, attrs=None, **kwargs):
		input_html = super(AdminSplitDateTime, self).render(name, value, attrs)
		input_html = re.findall('<input.+?>', input_html)
		return mark_safe(render_to_string('xadmin/widgets/datetime.html', context={
			'date_input_html': input_html[0],
			'time_input_html': input_html[1]
		}))

	def format_output(self, rendered_widgets):
		return mark_safe('<div class="datetime clearfix">%s%s</div>' %
		                 (rendered_widgets[0], rendered_widgets[1]))


class AdminRadioInput(RadioChoiceInput):

	def render(self, name=None, value=None, attrs=None, choices=()):
		name = name or self.name
		value = value or self.value
		attrs = attrs or self.attrs
		attrs['class'] = attrs.get('class', '').replace('form-control', '')
		if 'id' in self.attrs:
			label_for = ' for="%s_%s"' % (self.attrs['id'], self.index)
		else:
			label_for = ''
		choice_label = conditional_escape(force_text(self.choice_label))
		if attrs.get('inline', False):
			return mark_safe('<label%s class="radio-inline">%s %s</label>' % (label_for, self.tag(), choice_label))
		else:
			return mark_safe('<div class="radio"><label%s>%s %s</label></div>' % (label_for, self.tag(), choice_label))


class AdminRadioFieldRenderer(forms.RadioSelect):

	def __iter__(self):
		for i, choice in enumerate(self.choices):
			yield AdminRadioInput(self.name, self.value, self.attrs.copy(), choice, i)

	def __getitem__(self, idx):
		choice = self.choices[idx]  # Let the IndexError propogate
		return AdminRadioInput(self.name, self.value, self.attrs.copy(), choice, idx)

	def render(self, *args, **kwargs):
		return mark_safe('\n'.join([force_text(w) for w in self]))


class AdminRadioSelect(forms.RadioSelect):
	renderer = AdminRadioFieldRenderer


class AdminCheckboxSelect(forms.CheckboxSelectMultiple):

	def render(self, name, value, attrs=None, choices=(), **kwargs):
		if value is None:
			value = []
		has_id = attrs and 'id' in attrs
		final_attrs = self.build_attrs(attrs, extra_attrs={'name': name})
		output = []
		# Normalize to strings
		str_values = set([force_text(v) for v in value])
		for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
			# If an ID attribute was given, add a numeric index as a suffix,
			# so that the checkboxes don't all have the same ID attribute.
			if has_id:
				final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
				label_for = ' for="%s"' % final_attrs['id']
			else:
				label_for = ''

			cb = forms.CheckboxInput(
				final_attrs, check_test=lambda value: value in str_values)
			option_value = force_text(option_value)
			rendered_cb = cb.render(name, option_value)
			option_label = conditional_escape(force_text(option_label))

			if final_attrs.get('inline', False):
				output.append(
					'<label%s class="checkbox-inline">%s %s</label>' % (label_for, rendered_cb, option_label))
			else:
				output.append(
					'<div class="checkbox"><label%s>%s %s</label></div>' % (label_for, rendered_cb, option_label))
		return mark_safe('\n'.join(output))


class AdminSelectMultiple(forms.SelectMultiple):

	def __init__(self, attrs=None):
		final_attrs = {'class': 'select-multi'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminSelectMultiple, self).__init__(attrs=final_attrs)


class AdminFileWidget(forms.ClearableFileInput):
	template_name = 'xadmin/widgets/clearable_file_input.html'
	template_with_initial = ('<p class="file-upload">%s</p>'
	                         % forms.ClearableFileInput.initial_text)
	template_with_clear = ('<span class="clearable-file-input">%s</span>'
	                       % forms.ClearableFileInput.clear_checkbox_label)

	def __init__(self, attrs=None):
		final_attrs = {'class': 'custom-file-input'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminFileWidget, self).__init__(attrs=final_attrs)


class AdminTextareaWidget(forms.Textarea):

	def __init__(self, attrs=None):
		final_attrs = {'class': 'textarea-field'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminTextareaWidget, self).__init__(attrs=final_attrs)


class AdminTextInputWidget(forms.TextInput):

	def __init__(self, attrs=None):
		final_attrs = {'class': 'text-field'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminTextInputWidget, self).__init__(attrs=final_attrs)


class AdminURLFieldWidget(forms.URLInput):

	def __init__(self, attrs=None):
		final_attrs = {'class': 'url-field'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminURLFieldWidget, self).__init__(attrs=final_attrs)


class AdminIntegerFieldWidget(forms.NumberInput):

	def __init__(self, attrs=None):
		final_attrs = {'class': 'int-field'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminIntegerFieldWidget, self).__init__(attrs=final_attrs)


class AdminCommaSeparatedIntegerFieldWidget(forms.NumberInput):

	def __init__(self, attrs=None):
		final_attrs = {'class': 'sep-int-field'}
		if attrs is not None:
			final_attrs.update(attrs)
		super(AdminCommaSeparatedIntegerFieldWidget, self).__init__(attrs=final_attrs)
