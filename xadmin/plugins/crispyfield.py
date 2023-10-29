from crispy_forms.layout import LayoutObject
from crispy_forms.utils import TEMPLATE_PACK

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ModelFormAdminView


class CrispyFieldAdminPlugin(BaseAdminPlugin):
	"""
	The function of this plugin is to allow the configuration of a 'crispy field' for a form field.
	Example configuration:
	crispy_fields = {
		'field_name': {
			'field': SwitchCheckbox,
			'attrs': {}
		}
	}
	crispy_fields_overrides = {
		BooleanField: SwitchCheckbox
	}
	"""
	crispy_fields = {}
	crispy_fields_overrides = {}

	def init_request(self, *args, **kwargs):
		return bool(len(self.crispy_fields) or len(self.crispy_fields_overrides)
		            and TEMPLATE_PACK == "bootstrap4")

	def get_form_layout(self, layout):
		for pointer in layout.get_field_names():
			field_layout = layout
			for position in pointer.positions:
				layout_field_name = field_layout.fields[position]
				if isinstance(layout_field_name, LayoutObject):
					field_layout = layout_field_name
				if isinstance(layout_field_name, str):
					if field_opts := self.crispy_fields.get(layout_field_name):
						field_layout.fields[field_layout.fields.index(layout_field_name)] = (
							crispy_field(layout_field_name, **field_opts.get('attrs', {}))
							if (crispy_field := field_opts['field']) and callable(crispy_field) else
							crispy_field
						)
					elif form_obj := getattr(self.admin_view, "form_obj", None):
						try:
							form_field_class = type(form_obj.fields[layout_field_name])
						except KeyError:
							continue
						if layout_field_class := self.crispy_fields_overrides.get(form_field_class):
							layout_field_class = layout_field_class(layout_field_name) if callable(layout_field_class) else layout_field_class
							field_layout.fields[field_layout.fields.index(layout_field_name)] = layout_field_class
		return layout


site.register_plugin(CrispyFieldAdminPlugin, ModelFormAdminView)
