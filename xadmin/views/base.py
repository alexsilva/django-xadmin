import copy
import datetime
import decimal
import django.db.models
import functools
from collections import OrderedDict
from inspect import getfullargspec

from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_permission_codename
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.template import Context, Template
from django.template.response import TemplateResponse
from django.urls.base import reverse
from django.utils.decorators import method_decorator, classonlymethod
from django.utils.encoding import force_text, smart_text
from django.utils.functional import Promise
from django.utils.http import urlencode
from django.utils.itercompat import is_iterable
from django.utils.safestring import mark_safe
from django.utils.text import capfirst, Truncator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic import View

from xadmin.models import Log
from xadmin.util import static, json, vendor, sortkeypicker

csrf_protect_m = method_decorator(csrf_protect)


class IncorrectPluginArg(Exception):
	pass


def get_content_type_for_model(obj):
	from django.contrib.contenttypes.models import ContentType
	return ContentType.objects.get_for_model(obj, for_concrete_model=False)


def filter_chain(filters, token, func, *args, **kwargs):
	if token == -1:
		return func()
	else:
		def _inner_method():
			fm = filters[token]
			fargs = getfullargspec(fm)[0]
			if len(fargs) == 1:
				# Only self arg
				result = func()
				if result is None:
					return fm()
				else:
					raise IncorrectPluginArg('Plugin filter method need a arg to receive parent method result.')
			else:
				return fm(func if fargs[1] == '__' else func(), *args, **kwargs)

		return filter_chain(filters, token - 1, _inner_method, *args, **kwargs)


def filter_hook(func):
	tag = func.__name__
	func.__doc__ = "``filter_hook``\n\n" + (func.__doc__ or "")

	@functools.wraps(func)
	def method(self, *args, **kwargs):

		def _inner_method():
			return func(self, *args, **kwargs)

		if self.plugins:
			filters = [(getattr(getattr(p, tag), 'priority', 10), getattr(p, tag))
			           for p in self.plugins if callable(getattr(p, tag, None))]
			filters = [f for p, f in sorted(filters, key=lambda x: x[0])]
			return filter_chain(filters, len(filters) - 1, _inner_method, *args, **kwargs)
		else:
			return _inner_method()

	return method


def inclusion_tag(file_name, context_class=Context, takes_context=False):
	def wrap(func):
		@functools.wraps(func)
		def method(self, context, nodes, *arg, **kwargs):
			_dict = func(self, context, nodes, *arg, **kwargs)
			from django.template.loader import get_template, select_template
			if isinstance(file_name, Template):
				t = file_name
			elif not isinstance(file_name, str) and is_iterable(file_name):
				t = select_template(file_name)
			else:
				t = get_template(file_name)

			_dict['autoescape'] = context.autoescape
			_dict['use_l10n'] = context.use_l10n
			_dict['use_tz'] = context.use_tz
			_dict['admin_view'] = context['admin_view']

			csrf_token = context.get('csrf_token', None)
			if csrf_token is not None:
				_dict['csrf_token'] = csrf_token
			nodes.append(t.render(_dict))

		return method

	return wrap


class JSONEncoder(DjangoJSONEncoder):

	def default(self, o):
		if isinstance(o, datetime.datetime):
			return o.strftime('%Y-%m-%d %H:%M:%S')
		elif isinstance(o, datetime.date):
			return o.strftime('%Y-%m-%d')
		elif isinstance(o, decimal.Decimal):
			return str(o)
		elif isinstance(o, Promise):
			return force_text(o)
		else:
			try:
				return super(JSONEncoder, self).default(o)
			except Exception:
				return smart_text(o)


class BaseAdminMergeView:
	"""Reference class for merge view (Used to identify the final class)"""
	pass


class BaseAdminObject:

	def get_view(self, view_class, option_class=None, *args, **kwargs):
		opts = kwargs.pop('opts', {})
		view = self.admin_site.get_view_class(view_class, option_class, **opts)()
		view.setup(self.request, *args, **kwargs)
		return view

	def get_model_view(self, view_class, model, *args, **kwargs):
		return self.get_view(view_class, self.admin_site.get_registry(model, None), *args, **kwargs)

	def get_admin_url(self, name, *args, **kwargs):
		return reverse('%s:%s' % (self.admin_site.app_name, name), args=args, kwargs=kwargs)

	def get_model_url(self, model, name, *args, **kwargs):
		return reverse(
			'%s:%s_%s_%s' % (self.admin_site.app_name, model._meta.app_label,
			                 model._meta.model_name, name),
			args=args, kwargs=kwargs, current_app=self.admin_site.name)

	def get_model_perm(self, model, name):
		return '%s.%s_%s' % (model._meta.app_label, name, model._meta.model_name)

	def has_model_perm(self, model, name, user=None):
		user = user or self.user
		return user.has_perm(self.get_model_perm(model, name)) or (
					name == 'view' and self.has_model_perm(model, 'change', user))

	def has_object_perm(self, model, name, user=None, obj=None):
		"""Validation of permissions for the object"""
		user = user or self.user
		return user.has_perm(self.get_model_perm(model, name), obj) or (
					name == 'view' and self.has_object_perm(model, 'change', user=user, obj=obj))

	def get_query_string(self, new_params=None, remove=None):
		if new_params is None:
			new_params = {}
		if remove is None:
			remove = []
		p = dict(self.request.GET.items()).copy()
		arr_keys = list(p.keys())
		for r in remove:
			for k in arr_keys:
				if k.startswith(r):
					del p[k]
		for k, v in new_params.items():
			if v is None:
				if k in p:
					del p[k]
			else:
				p[k] = v
		return '?%s' % urlencode(p)

	def get_form_params(self, new_params=None, remove=None):
		if new_params is None:
			new_params = {}
		if remove is None:
			remove = []
		p = dict(self.request.GET.items()).copy()
		arr_keys = list(p.keys())
		for r in remove:
			for k in arr_keys:
				if k.startswith(r):
					del p[k]
		for k, v in new_params.items():
			if v is None:
				if k in p:
					del p[k]
			else:
				p[k] = v
		return mark_safe(''.join(
			'<input type="hidden" name="%s" value="%s"/>' % (k, v) for k, v in p.items() if v))

	def render_response(self, content, response_type='json'):
		if response_type == 'json':
			response = HttpResponse(content_type="application/json; charset=UTF-8")
			response.write(
				json.dumps(content, cls=JSONEncoder, ensure_ascii=False))
			return response
		return HttpResponse(content)

	def template_response(self, template, context):
		return TemplateResponse(self.request, template, context)

	def message_user(self, message, level='info'):
		"""
		Send a message to the user. The default implementation
		posts a message using the django.contrib.messages backend.
		"""
		if hasattr(messages, level) and callable(getattr(messages, level)):
			getattr(messages, level)(self.request, message)

	def static(self, path):
		return static(path)

	def vendor(self, *tags):
		return vendor(*tags)

	def log(self, flag, message, obj=None):
		log = Log(
			user=self.user,
			ip_addr=self.request.META['REMOTE_ADDR'],
			action_flag=flag,
			message=message
		)
		if obj:
			log.content_type = get_content_type_for_model(obj)
			log.object_id = obj.pk
			# Limits the representation to the maximum size of the field.
			log.object_repr = Truncator(force_text(obj)).chars(log.object_repr_length)
		log.save()
		return log


@functools.total_ordering
class BaseAdminPlugin(BaseAdminObject):
	__order__ = 100  # load order

	def __init__(self, admin_view):
		self.admin_view = admin_view
		self.admin_site = admin_view.admin_site
		self.request = admin_view.request
		self.user = admin_view.user
		self.args = admin_view.args
		self.kwargs = admin_view.kwargs

		if hasattr(admin_view, 'model'):
			self.model = admin_view.model
			self.opts = admin_view.model._meta

	def __lt__(self, plugin):
		return self.__order__ < plugin.__order__

	def __eq__(self, plugin):
		return self.__order__ == plugin.__order__

	def init_request(self, *args, **kwargs):
		"""Initializes the activation of the plugin (Returning False makes the plugin disabled)"""
		pass

	def setup(self, *args, **kwargs):
		"""Configure the plugin after activation"""
		pass

	def has_object_site_perm(self, view_class, model, obj, perm_name, **options):
		"""Permission validation for the object (including the view)"""
		has_change_perm = self.has_object_perm(model, perm_name, obj=obj)
		if not has_change_perm:
			# validates permission for the object
			opts = self.admin_site.get_registry(model, None)
			view = self.admin_site.get_view_class(view_class, opts)()
			# The view needs to have a method for validating the object.
			permission_method = f"has_{perm_name}_permission"
			if not hasattr(view, permission_method):
				return has_change_perm
			try:
				# remove plugin from list to not initialize recursively.
				view.plugin_classes.remove(type(self))
			except ValueError:
				pass
			request = options.get('request', self.request)
			args = options.get('args', self.args)
			kwargs = options.get('kwargs', self.kwargs)
			view.setup(request, *args, **kwargs)
			has_change_perm = getattr(view, permission_method)(obj=obj)
		return has_change_perm

	def has_object_view_permission(self, view_class, model: django.db.models.Model, obj, **options):
		return self.has_object_site_perm(view_class, model, obj, "view", **options)

	def has_object_add_permission(self, view_class, model: django.db.models.Model, obj, **options):
		return self.has_object_site_perm(view_class, model, obj, "add", **options)

	def has_object_change_permission(self, view_class, model: django.db.models.Model, obj, **options):
		return self.has_object_site_perm(view_class, model, obj, "change", **options)

	def has_object_delete_permission(self, view_class, model: django.db.models.Model, obj, **options):
		return self.has_object_site_perm(view_class, model, obj, "delete", **options)


class PluginManager:
	"""Manages plugins initialization"""

	def __init__(self, admin_view):
		self.base_plugins = sorted(getattr(admin_view, "plugin_classes", ()),
		                           key=lambda plugin: plugin.__order__)
		self.admin_view = admin_view

	def init(self, *initargs, **initkwargs):
		"""Instance of plugins linking them to admin view"""
		plugins = []
		view = self.admin_view
		for plugin_class in self.base_plugins:
			plg = plugin_class(view)
			active = plg.init_request(*initargs, **initkwargs)
			if active is not False:
				plg.setup(*initargs, **initkwargs)
				plugins.append(plg)
		# active plugins ordered
		return sorted(plugins)


class BaseAdminView(BaseAdminObject, View):
	""" Base Admin view, support some comm attrs."""

	base_template = 'xadmin/base.html'
	need_site_permission = True

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.request_method = None
		self.plugin_manager = None
		self.user = None

	def setup(self, request, *args, **kwargs):
		super().setup(request, *args, **kwargs)
		self.request_method = request.method.lower()
		self.user = request.user

		self.plugin_manager = PluginManager(self)

		self.init_plugin(*args, **kwargs)
		self.init_request(*args, **kwargs)
		self.setup_view(*args, **kwargs)

	def init_request(self, *args, **kwargs):
		pass

	@filter_hook
	def setup_view(self, *args, **kwargs):
		pass

	def init_plugin(self, *args, **kwargs):
		self.plugins = self.plugin_manager.init(*args, **kwargs)

	@filter_hook
	def get_context(self):
		return {'admin_view': self, 'media': self.media, 'base_template': self.base_template}

	@property
	def media(self):
		return self.get_media()

	@filter_hook
	def get_media(self):
		return forms.Media()

	@classonlymethod
	def as_view(cls, *initargs, **initkwargs):
		view = super().as_view(*initargs, **initkwargs)
		view.need_site_permission = cls.need_site_permission
		return view


class CommAdminView(BaseAdminView):
	base_template = 'xadmin/base_site.html'
	menu_template = 'xadmin/includes/sitemenu_default.html'

	site_title = getattr(settings, "XADMIN_TITLE", _("Django Xadmin"))
	site_footer = getattr(settings, "XADMIN_FOOTER_TITLE", _("my-company.inc"))

	global_models_icon = {}
	default_model_icon = None
	apps_label_title = {}
	apps_icons = {}

	def get_site_menu(self):
		return None

	@filter_hook
	def hidden_model_menu(self, model, model_admin):
		"""Hook that lets you configure menus dynamically through plugins
		'hidden_menu' when defined in model-admin, represents a static configuration
		and this creates problems in a multithreads environment.
		Example usage:
			class MenuHiddenPlugin(BaseAdminPlugin):
				# Example of a plugin that changes the default setting given in model-admin
				def hidden_model_menu(self, hidden_menu, model, model_admin):
					return not hidden_menu
		"""
		return getattr(model_admin, 'hidden_menu', False)

	@filter_hook
	def get_nav_menu(self):
		site_menu = list(self.get_site_menu() or [])
		had_urls = []

		def get_url(menu, had_urls):
			if 'url' in menu:
				had_urls.append(menu['url'])
			if 'menus' in menu:
				for m in menu['menus']:
					get_url(m, had_urls)

		get_url({'menus': site_menu}, had_urls)

		nav_menu = OrderedDict()

		for model, model_admin in self.admin_site._registry.items():
			# Menus will be shown based on model-admin configuration or plugins.
			if self.hidden_model_menu(model, model_admin):
				continue
			app_label = model._meta.app_label
			app_icon = None
			model_dict = {
				'title': smart_text(capfirst(model._meta.verbose_name_plural)),
				'url': self.get_model_url(model, "changelist"),
				'icon': self.get_model_icon(model),
				'perm': self.get_model_perm(model, 'view'),
				'order': model_admin.order,
			}
			if model_dict['url'] in had_urls:
				continue

			app_key = "app:%s" % app_label
			if app_key in nav_menu:
				nav_menu[app_key]['menus'].append(model_dict)
			else:
				# Find app title
				app_title = smart_text(app_label.title())
				if app_label.lower() in self.apps_label_title:
					app_title = self.apps_label_title[app_label.lower()]
				else:
					app_title = smart_text(apps.get_app_config(app_label).verbose_name)
				# find app icon
				if app_label.lower() in self.apps_icons:
					app_icon = self.apps_icons[app_label.lower()]

				nav_menu[app_key] = {
					'title': app_title,
					'menus': [model_dict],
				}

			app_menu = nav_menu[app_key]
			if app_icon:
				app_menu['first_icon'] = app_icon
			elif ('first_icon' not in app_menu or
			      app_menu['first_icon'] == self.default_model_icon) and model_dict.get('icon'):
				app_menu['first_icon'] = model_dict['icon']

			if 'first_url' not in app_menu and model_dict.get('url'):
				app_menu['first_url'] = model_dict['url']

		for menu in nav_menu.values():
			menu['menus'].sort(key=sortkeypicker(['order', 'title']))

		nav_menu = list(nav_menu.values())
		nav_menu.sort(key=lambda x: x['title'])

		site_menu.extend(nav_menu)

		return site_menu

	@filter_hook
	def has_session_nav_menu(self):
		return not settings.DEBUG and 'nav_menu' in self.request.session

	@filter_hook
	def get_context(self):
		context = super(CommAdminView, self).get_context()

		if self.has_session_nav_menu():
			nav_menu = json.loads(self.request.session['nav_menu'])
		else:
			menus = copy.copy(self.get_nav_menu())

			def check_menu_permission(item):
				need_perm = item.pop('perm', None)
				if need_perm is None:
					return True
				elif callable(need_perm):
					return need_perm(self.user)
				elif need_perm == 'super':
					return self.user.is_superuser
				else:
					return self.user.has_perm(need_perm)

			def filter_item(item):
				if 'menus' in item:
					before_filter_length = len(item['menus'])
					item['menus'] = [filter_item(
						i) for i in item['menus'] if check_menu_permission(i)]
					after_filter_length = len(item['menus'])
					if after_filter_length == 0 and before_filter_length > 0:
						return None
				return item

			nav_menu = [filter_item(item) for item in menus if check_menu_permission(item)]
			nav_menu = list(filter(lambda x: x, nav_menu))

			if not settings.DEBUG:
				self.request.session['nav_menu'] = json.dumps(nav_menu, cls=JSONEncoder, ensure_ascii=False)
				self.request.session.modified = True

		def check_selected(menu, path):
			selected = False
			if 'url' in menu:
				chop_index = menu['url'].find('?')
				if chop_index == -1:
					selected = path.startswith(menu['url'])
				else:
					selected = path.startswith(menu['url'][:chop_index])
			if 'menus' in menu:
				for m in menu['menus']:
					_s = check_selected(m, path)
					if _s:
						selected = True
			if selected:
				menu['selected'] = True
			return selected

		for menu in nav_menu:
			check_selected(menu, self.request.path)

		context.update({
			'menu_template': self.menu_template,
			'nav_menu': nav_menu,
			'site_title': self.site_title,
			'site_footer': self.site_footer,
			'breadcrumbs': self.get_breadcrumb()
		})

		return context

	@filter_hook
	def get_model_icon(self, model):
		icon = self.global_models_icon.get(model)
		if icon is None and model in self.admin_site._registry:
			icon = getattr(self.admin_site._registry[model],
			               'model_icon', self.default_model_icon)
		return icon

	@filter_hook
	def get_breadcrumb(self):
		return [{
			'url': self.get_admin_url('index'),
			'title': _('Home')
		}]


class ModelAdminView(CommAdminView):
	fields = None
	exclude = None
	ordering = None
	model = None
	remove_permissions = []

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# model options
		self.opts = self.model._meta
		self.app_label = self.opts.app_label
		self.model_name = self.opts.model_name
		self.model_info = (self.app_label, self.model_name)

	@filter_hook
	def log_obj(self, flag, message, obj):
		"""hook that allows plugins to access logs for edited objects."""
		return super().log(flag, message, obj)

	def log(self, flag, message, obj=None):
		return self.log_obj(flag, message, obj)

	@filter_hook
	def get_context(self):
		new_context = {
			"opts": self.opts,
			"app_label": self.app_label,
			"model_name": self.model_name,
			"verbose_name": force_text(self.opts.verbose_name),
			'model_icon': self.get_model_icon(self.model),
		}
		context = super(ModelAdminView, self).get_context()
		context.update(new_context)
		return context

	@filter_hook
	def get_breadcrumb(self):
		bcs = super(ModelAdminView, self).get_breadcrumb()
		item = {'title': self.opts.verbose_name_plural}
		if self.has_view_permission():
			item['url'] = self.model_admin_url('changelist')
		bcs.append(item)
		return bcs

	@filter_hook
	def get_object(self, object_id):
		"""
		Get model object instance by object_id, used for change admin view
		"""
		# first get base admin view property queryset, return default model queryset
		model = self.model
		try:
			object_id = model._meta.pk.to_python(object_id)
			return model.objects.get(pk=object_id)
		except (model.DoesNotExist, ValidationError):
			return None

	@filter_hook
	def get_object_url(self, obj):
		if self.has_change_permission(obj):
			return self.model_admin_url("change", getattr(obj, self.opts.pk.attname))
		elif self.has_view_permission(obj):
			return self.model_admin_url("detail", getattr(obj, self.opts.pk.attname))
		else:
			return None

	def model_admin_url(self, name, *args, **kwargs):
		"""Reverts the model url in the admin view"""
		return self.get_model_url(self.model, name, *args, **kwargs)

	def get_model_perms(self):
		"""
		Returns a dict of all perms for this model. This dict has the keys
		``add``, ``change``, and ``delete`` mapping to the True/False for each
		of those actions.
		"""
		return {
			'view': self.has_view_permission(),
			'add': self.has_add_permission(),
			'change': self.has_change_permission(),
			'delete': self.has_delete_permission(),
		}

	def get_template_list(self, template_name):
		opts = self.opts
		return (
			"xadmin/%s/%s/%s" % (
				opts.app_label, opts.object_name.lower(), template_name),
			"xadmin/%s/%s" % (opts.app_label, template_name),
			"xadmin/%s" % template_name,
		)

	def get_ordering(self):
		"""
		Hook for specifying field ordering.
		"""
		return self.ordering or ()  # otherwise we might try to *None, which is bad ;)

	@filter_hook
	def queryset(self):
		"""
		Returns a QuerySet of all model instances that can be edited by the
		admin site. This is used by changelist_view.
		"""
		return self.model._default_manager.get_queryset()

	def has_auth_permission(self, name: str, obj=None):
		"""
		:param obj: instance of model
		:param name: permission name
		"""
		permission_codename = get_permission_codename(name, self.opts)
		return self.user.has_perm('%s.%s' % (self.opts.app_label, permission_codename))

	def has_view_permission(self, obj=None):
		return ('view' not in self.remove_permissions) and (self.has_auth_permission("view", obj) or
		                                                    self.has_auth_permission("change", obj))

	def has_add_permission(self, obj=None):
		return ('add' not in self.remove_permissions) and self.has_auth_permission("add", obj)

	def has_change_permission(self, obj=None):
		return ('change' not in self.remove_permissions) and self.has_auth_permission("change", obj)

	def has_delete_permission(self, obj=None):
		return ('delete' not in self.remove_permissions) and self.has_auth_permission("delete", obj)
