from django.db import models
from django.urls.base import NoReverseMatch
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView, DetailAdminView, UpdateAdminView


class DetailsPlugin(BaseAdminPlugin):
	show_detail_fields = []
	show_all_rel_details = True

	def result_item(self, item, obj, field_name, row):
		if self.show_all_rel_details or field_name in self.show_detail_fields:
			rel_obj = None
			if hasattr(item.field, 'remote_field') and isinstance(item.field.remote_field, models.ManyToOneRel):
				rel_obj = getattr(obj, field_name)
			elif field_name in self.show_detail_fields:
				rel_obj = obj

			if rel_obj:
				rel_model = type(rel_obj)
				if model_admin := site.get_registry(rel_model, None):
					try:
						has_view_perm = self.get_view(DetailAdminView, model_admin, rel_obj.pk).has_view_permission(rel_obj)
						has_change_perm = self.get_view(UpdateAdminView, model_admin, rel_obj.pk).has_change_permission(rel_obj)
					except Exception as exc:
						has_view_perm = self.admin_view.has_model_perm(rel_model, 'view')
						has_change_perm = self.has_model_perm(rel_model, 'change')
				else:
					has_view_perm = self.admin_view.has_model_perm(rel_model, 'view')
					has_change_perm = self.has_model_perm(rel_model, 'change')
			else:
				has_view_perm = has_change_perm = False
			if rel_obj and has_view_perm:
				rel_model = type(rel_obj)
				opts = rel_model._meta
				try:
					item_res_uri = self.get_model_url(rel_model, 'detail', getattr(rel_obj, opts.pk.attname))
					if item_res_uri:
						if has_change_perm:
							edit_url = self.get_model_url(rel_model, 'change', getattr(rel_obj, opts.pk.attname))
						else:
							edit_url = ''

						detail_title = _('Details of %s') % escape(str(rel_obj))
						detail_btn = mark_safe(f'''
						<a data-res-uri="{item_res_uri}" href="#" data-edit-uri="{edit_url}" class="details-handler" 
							rel="tooltip" title="{detail_title}"><i class="fa fa-info-circle"></i>
						</a>
		                ''')
						item.btns.append(detail_btn)
				except NoReverseMatch:
					pass
		return item

	# Media
	def get_media(self, media):
		if self.show_all_rel_details or self.show_detail_fields:
			media = media + self.vendor('xadmin.plugin.details.js', 'xadmin.form.css')
		return media


site.register_plugin(DetailsPlugin, ListAdminView)
