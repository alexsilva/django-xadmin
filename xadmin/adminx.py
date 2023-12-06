from django.utils.translation import gettext_lazy as _

import xadmin
from xadmin.models import UserSettings, Log


class UserSettingsAdmin:
	model_icon = 'fa fa-cog'
	hidden_menu = True


xadmin.site.register(UserSettings, UserSettingsAdmin)


class LogAdmin:

	def link(self, instance):
		if instance.content_type and instance.object_id and instance.action_flag != 'delete':
			admin_url = self.get_admin_url('%s_%s_change' % (instance.content_type.app_label,
			                                                 instance.content_type.model),
			                               instance.object_id)
			text = _('Admin Object')
			target = getattr(self.link, "target", "")
			return f"<a href='{admin_url}' target='{target}'>{text}</a>"
		else:
			return ''

	link.short_description = ""
	link.allow_tags = True
	link.is_column = False
	link.target = "_blank"

	list_display = ('action_time', 'user', 'ip_addr', '__str__', 'link')
	list_filter = ['user', 'action_time']
	search_fields = ['ip_addr', 'message']
	model_icon = 'fa fa-cog'


xadmin.site.register(Log, LogAdmin)
