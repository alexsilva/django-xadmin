# coding:utf-8
import cgi
import urllib.parse

import httplib2
from django.core.cache import cache, DEFAULT_CACHE_ALIAS, caches
from django.core.cache.backends.dummy import DummyCache
from django.template import loader
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _

from xadmin.models import UserSettings
from xadmin.sites import site
from xadmin.util import static, json
from xadmin.views import BaseAdminPlugin, BaseAdminView

THEME_CACHE_KEY = 'xadmin_themes'


class ThemePlugin(BaseAdminPlugin):
	enable_themes = False
	user_themes = None
	use_bootswatch = False

	@cached_property
	def default_theme(self):
		return static('xadmin/css/themes/bootstrap-xadmin.css')

	@cached_property
	def bootstrap4_theme(self):
		return static('xadmin/css/themes/bootstrap.litera.min.css')

	def init_request(self, *args, **kwargs):
		return self.enable_themes

	def _get_theme(self):
		if self.user:
			try:
				return UserSettings.objects.get(user=self.user, key="site-theme").value
			except Exception:
				pass
		if '_theme' in self.request.COOKIES:
			return urllib.parse.unquote(self.request.COOKIES['_theme'])
		return self.default_theme

	def get_context(self, context):
		if not context.get('site_theme'):
			context['site_theme'] = self._get_theme()
		return context

	def cache(self, key):
		"""get cache themes"""
		cache = caches[DEFAULT_CACHE_ALIAS]
		if isinstance(cache, DummyCache):
			return getattr(self.admin_site, 'ext_themes', None)
		ext_themes = cache.get(THEME_CACHE_KEY)
		return ext_themes and json.loads(ext_themes)

	# Media
	def get_media(self, media):
		return media + self.vendor('jquery-ui-effect.js', 'xadmin.plugin.themes.js')

	# Block Views
	def block_top_navmenu(self, context, nodes):

		themes = [
			{'name': _("Default"), 'description': _("Default bootstrap theme"), 'css': self.default_theme},
			{'name': _("Bootstrap4"), 'description': _("Bootstrap 4.x theme"), 'css': self.bootstrap4_theme},
		]
		select_css = context.get('site_theme', self.default_theme)

		if self.user_themes:
			themes.extend(self.user_themes)

		if self.use_bootswatch:
			ext_themes = self.cache(THEME_CACHE_KEY)
			if ext_themes:
				themes.extend(ext_themes)
			else:
				ext_themes = []
				try:
					h = httplib2.Http()
					resp, content = h.request("https://bootswatch.com/api/4.json", 'GET', '',
					                          headers={"Accept": "application/json",
					                                   "User-Agent": self.request.META['HTTP_USER_AGENT']})
					mimetype, spec = cgi.parse_header(resp.get('content-type', ''))
					content = content.decode(spec.get('charset', 'UTF-8'))
					watch_themes = json.loads(content)['themes']
					ext_themes.extend([
						{'name': t['name'], 'description': t['description'],
						 'css': t['cssMin'], 'thumbnail': t['thumbnail']}
						for t in watch_themes])
				except Exception as e:
					print(e)

				cache.set(THEME_CACHE_KEY, json.dumps(ext_themes), 24 * 3600)
				self.admin_site.ext_themes = ext_themes  # temporary cache
				themes.extend(ext_themes)

		nodes.append(loader.render_to_string('xadmin/blocks/comm.top.theme.html', {
			'themes': themes, 'select_css': select_css
		}))


site.register_plugin(ThemePlugin, BaseAdminView)
