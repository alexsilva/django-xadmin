# coding=utf-8
import math

from crispy_forms import bootstrap
from crispy_forms import helper
from crispy_forms import layout
from crispy_forms.bootstrap import *
from crispy_forms.layout import *
from crispy_forms.utils import render_field, TEMPLATE_PACK

# local reference to prevent optimization tools from removing the import
FormHelper = helper.FormHelper
bootstrap = bootstrap


class Fieldset(layout.Fieldset):
	template = "xadmin/layout/fieldset.html"

	def __init__(self, legend, *fields, **kwargs):
		self.description = kwargs.pop('description', None)
		self.collapsed = kwargs.pop('collapsed', None)
		super(Fieldset, self).__init__(legend, *fields, **kwargs)


class Row(layout.Div):

	def __init__(self, *fields, **kwargs):
		css_class = 'form-row'

		new_fields = [self.convert_field(f, len(fields)) for f in fields]
		super(Row, self).__init__(css_class=css_class, *new_fields, **kwargs)

	def convert_field(self, f, counts):
		col_class = "col-sm-%d" % int(math.ceil(12 / counts))
		if not (isinstance(f, layout.Field) or issubclass(f.__class__, Field)):
			f = layout.Field(f)
		if f.wrapper_class:
			f.wrapper_class += " %s" % col_class
		else:
			f.wrapper_class = col_class
		return f


class Col(layout.Column):

	def __init__(self, id, *fields, **kwargs):
		css_class = ['column', 'form-column', id, 'col col-sm-%d' %
		             kwargs.get('span', 6)]
		if kwargs.get('horizontal'):
			css_class.append('form-horizontal')
		super(Col, self).__init__(css_class=' '.join(css_class), *
		fields, **kwargs)


class Main(layout.Column):
	css_class = "column form-column main col-12 col-xl-9 form-horizontal"


class Side(layout.Column):
	css_class = "column form-column sidebar col-12 col-xl-3"


class Container(layout.Div):
	css_class = "form-container row clearfix"


# Override bootstrap4
class InputGroup(layout.Field):
	template = "xadmin/layout/input_group.html"

	def __init__(self, field, *args, **kwargs):
		self.field = field
		self.inputs = list(args)
		if '@@' not in args:
			self.inputs.append('@@')

		self.input_size = None
		css_class = kwargs.get('css_class', '')
		if 'input-lg' in css_class:
			self.input_size = 'input-group-lg'
		if 'input-sm' in css_class:
			self.input_size = 'input-group-sm'

		super(InputGroup, self).__init__(field, **kwargs)

	def render(self, form, context, **kwargs):
		extra_context = {
			'inputs': self.inputs,
			'input_size': self.input_size,
		}
		if hasattr(self, 'wrapper_class'):
			extra_context['wrapper_class'] = self.wrapper_class

		return render_field(self.field, form, context, template=self.template,
		                    attrs=self.attrs, extra_context=extra_context,
		                    **kwargs)


class PrependedText(InputGroup):

	def __init__(self, field, text, **kwargs):
		super(PrependedText, self).__init__(field, text, '@@', **kwargs)


class AppendedText(InputGroup):

	def __init__(self, field, text, **kwargs):
		super(AppendedText, self).__init__(field, '@@', text, **kwargs)


class PrependedAppendedText(InputGroup):

	def __init__(self, field, prepended_text=None, appended_text=None, *args, **kwargs):
		super(PrependedAppendedText, self).__init__(
			field, prepended_text, '@@', appended_text, **kwargs)
