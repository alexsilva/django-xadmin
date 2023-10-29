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
	"""
	crispy_fields = {}

	def init_request(self, *args, **kwargs):
		return bool(len(self.crispy_fields) and TEMPLATE_PACK == "bootstrap4")

	def get_full_layout(self, layout, fields, **options):
		for pointer in layout.get_field_names():
			field_layout = layout
			for position in pointer.positions:
				field_layout = field_layout.fields[position]
				for field_name in self.crispy_fields:
					if isinstance(field_layout, LayoutObject) and field_name in field_layout.fields:
						field_opts = self.crispy_fields[field_name]
						field_layout.fields[field_layout.fields.index(field_name)] = (
							crispy_field(field_name, **field_opts.get('attrs', {}))
							if (crispy_field := field_opts['field']) and callable(crispy_field) else
							crispy_field
						)
		return layout


site.register_plugin(CrispyFieldAdminPlugin, ModelFormAdminView)
