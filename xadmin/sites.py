# coding=utf-8
import functools
import inspect
from functools import update_wrapper
from django.template.engine import Engine
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.urls import include, path as dj_path, re_path
from django.views.decorators.cache import never_cache


class AlreadyRegistered(Exception):
	pass


class NotRegistered(Exception):
	pass


class MergeAdminMetaclass(type):

	def __new__(cls, name, bases, attrs):
		# classe de referência para o novo objeto
		from xadmin.views.base import BaseAdminMergeView
		return super().__new__(cls, str(name), (BaseAdminMergeView,) + bases, attrs)


class AdminRoute:
	"""Rota para incluir outras urls"""
	path = re_path

	def __init__(self, route, app_name=None, namespace=None):
		self.route = route
		self.app_name = app_name
		self.namespace = namespace

	def __call__(self, urlpatterns):
		include_ns = include((urlpatterns, self.app_name),
		                     namespace=self.namespace)
		return self.path(self.route, include_ns)


@functools.total_ordering
class AdminUrl:
	"""Semelhante a urls django, guarda as definições de uma view
	"""
	path = re_path

	def __init__(self, route, cls_func, name=None, **kwargs):
		self.route = route
		self.cls_func = cls_func
		self.name = name
		self.kwargs = kwargs.get('kwargs')
		self.options = kwargs.get('options')  # legacy option
		self.initargs = kwargs.get('initargs')
		self.initkwargs = kwargs.get('initkwargs', self.options)
		self.include = AdminRoute(route, kwargs.get('app_name'),
		                          kwargs.get('namespace'))
		# se a view pode ser armazena com segurança no cache.
		self.cacheable = False
		# prioridade de carregamento
		self.priority = kwargs.get('priority', 100)
		self.include.path = self.path

	def __call__(self, view, route=None, **options):
		"""Constrói a url das configurações do objeto"""
		route = route or self.route
		options.setdefault('name', self.name)
		options.setdefault('kwargs', self.kwargs)
		return self.path(route, view, **options)

	def __str__(self):
		return f'{self.route} {self.cls_func} {self.name}'

	def __lt__(self, url):
		return self.priority < url.priority

	def __eq__(self, url):
		return self.priority == url.priority


class AdminPath(AdminUrl):
	"""Especificação de urls que não usam pattern"""
	path = dj_path


class AdminOptionClass:
	def __init__(self, model):
		self.model = model
		self.opts = model._meta
		self.items = []

	def __iter__(self):
		return iter(self.items)

	def append(self, admin_class):
		self.items.insert(0, admin_class)

	def __getattr__(self, name):
		return getattr(self.resolve(), name)

	def resolve(self):
		return type(str("%s%sAdmin" % (self.opts.app_label, self.opts.model_name)),
		            tuple(self.items), {})


class AdminSite:
	"""
	Website administration
	"""

	def __init__(self, name=None, app_name=None):
		self.name = name or 'xadmin'
		self.app_name = app_name or 'xadmin'

		# the instance will be ready when autodiscover runs successfully
		self.ready = False

		self._registry = {}  # model_class class -> admin_class class
		self._registry_avs = {}  # view_class class -> admin_class class
		self._registry_settings = {}  # settings name -> admin_class class
		self._registry_views = []
		# url instance contains (path, admin_view class, name)
		self._registry_modelviews = []
		# url instance contains (path, admin_view class, name)
		self._registry_plugins = {}  # admin_class class -> plugin_class class

		self._admin_view_cache = {}
		self._admin_view_opts_cache = {}
		self._admin_plugins_cache = {}

		self.model_admins_order = 0

	def copy_registry(self):
		import copy
		return {
			'models': copy.copy(self._registry),
			'avs': copy.copy(self._registry_avs),
			'views': copy.copy(self._registry_views),
			'settings': copy.copy(self._registry_settings),
			'modelviews': copy.copy(self._registry_modelviews),
			'plugins': copy.copy(self._registry_plugins),
		}

	def restore_registry(self, data):
		self._registry = data['models']
		self._registry_avs = data['avs']
		self._registry_views = data['views']
		self._registry_settings = data['settings']
		self._registry_modelviews = data['modelviews']
		self._registry_plugins = data['plugins']

	def register_modelview(self, path, view_class, name):
		from xadmin.views.base import BaseAdminView
		if issubclass(view_class, BaseAdminView):
			if not isinstance(path, (AdminUrl, AdminPath)):
				if view_class is None:
					raise ImproperlyConfigured('view_class not set!')
				path = AdminUrl(path, view_class, name)
			self._registry_modelviews.append(path)
		else:
			raise ImproperlyConfigured('The registered view class %s isn\'t subclass of %s' %
			                           (view_class.__name__, BaseAdminView.__name__))

	def register_view(self, path, view_class=None, name=None, **kwargs):
		"""Register a new view on the website (BaseAdminView)"""
		if not isinstance(path, (AdminUrl, AdminPath)):
			if view_class is None:
				raise ImproperlyConfigured('view_class not set!')
			path = AdminUrl(path, view_class, name, **kwargs)
		self._registry_views.append(path)

	def update_view(self, path, view_class, name, target_name=None, **kwargs):
		"""Register / update a view based on the path"""
		for index, url in enumerate(self._registry_views):
			# o tipo padrão é hidra url
			if isinstance(url, (list, tuple)):
				url = AdminUrl(*url)
			elif not isinstance(url, (AdminUrl, AdminPath)):
				url = AdminUrl(None, url)
			if target_name is None:
				target_name = name
			# atualiza o registro interno
			if url.route == path and url.name == target_name:
				klass = url.__class__
				# transforma em um objeto
				self._registry_views[index] = klass(path, view_class, name, **kwargs)
				break
		else:
			raise ImproperlyConfigured("View path/name does not exist.")

	def register_views(self, path, views=None, app_name=None, namespace=None, **kwargs):
		"""Registers views with a namespace"""
		if not isinstance(path, (AdminUrl, AdminPath)):
			if views is None:
				raise ImproperlyConfigured('view list not set!')
			path = AdminUrl(path, views, None, app_name=app_name, namespace=namespace, **kwargs)
		self._registry_views.append(path)

	def register_plugin(self, plugin_class, view_class):
		from xadmin.views.base import BaseAdminPlugin
		if inspect.isclass(plugin_class) and issubclass(plugin_class, BaseAdminPlugin):
			self._registry_plugins.setdefault(view_class, []).append(plugin_class)
		else:
			raise ImproperlyConfigured('The registered plugin class %s isn\'t subclass of %s' %
			                           (plugin_class.__name__, BaseAdminPlugin.__name__))

	def register_plugins(self, view_class, *plugin_classes):
		"""Plugin list register"""
		for plugin_class in plugin_classes:
			self.register_plugin(plugin_class, view_class)

	def unregister_plugin(self, view_class, *plugin_classes):
		"""Allows you to remove a plugin from the registry
		:param view_class: Class that subclass BaseAdminView.
		:param plugin_classes: Plugins (subclass / BaseAdminPlugin) that must be unregistered.
		"""
		from xadmin.views.base import BaseAdminPlugin
		from xadmin.views.base import BaseAdminView
		if not inspect.isclass(view_class) or not issubclass(view_class, BaseAdminView):
			raise ImproperlyConfigured('The registered view class %s isn\'t subclass of %s' %
			                           (view_class.__name__, BaseAdminView.__name__))
		for plugin_class in plugin_classes:
			if issubclass(plugin_class, BaseAdminPlugin):
				try:
					self._registry_plugins[view_class].remove(plugin_class)
				except ValueError:
					raise NotRegistered('Plugin \"%s\" was not registered' % plugin_class.__name__)
			else:
				raise ImproperlyConfigured('The registered plugin class %s isn\'t subclass of %s' %
				                           (plugin_class.__name__, BaseAdminPlugin.__name__))

	def register_settings(self, name, admin_class):
		self._registry_settings[name.lower()] = admin_class

	def get_registry(self, model_or_view, *args):
		"""Returns the options class registered for the model/view"""
		try:
			if isinstance(model_or_view, ModelBase):
				return self._registry[model_or_view]
			else:
				return self._registry_avs[model_or_view]
		except KeyError:
			if not args:
				raise NotRegistered('The model/view %s is not registered' % model_or_view.__name__)
			return args[0]

	def register(self, model_or_iterable, admin_class=object, **options):
		from xadmin.views.base import BaseAdminView
		if isinstance(model_or_iterable, ModelBase) or issubclass(model_or_iterable, BaseAdminView):
			model_or_iterable = [model_or_iterable]
		for model in model_or_iterable:
			if isinstance(model, ModelBase):
				model_opts = model._meta
				if model_opts.abstract:
					raise ImproperlyConfigured('The model %s is abstract, so it '
					                           'cannot be registered with admin.' % model.__name__)
				elif self.ready:
					raise ImproperlyConfigured("It is not possible to register model and options"
					                           " when the admin site is ready.")
				elif (registry := self._registry.get(model)) is None:
					# If we got **options then dynamically construct a subclass of
					# admin_class with those **options.
					if options:
						# For reasons I don't quite understand, without a __module__
						# the created class appears to "live" in the wrong place,
						# which causes issues later on.
						options['__module__'] = __name__

					admin_class = type(str("%s%sAdmin" % (model_opts.app_label, model_opts.model_name)), (admin_class,),
					                   options or {})

					admin_class.model = model
					admin_class.order = self.model_admins_order
					self.model_admins_order += 1

					self._registry[model] = registry = AdminOptionClass(model)
				elif admin_class in self._registry[model]:
					raise AlreadyRegistered(f"Admin class '{admin_class.__name__}' "
					                        f"already registered for the model '{model.__name__}'")

				registry.append(admin_class)
			else:
				if options:
					options['__module__'] = __name__
					admin_class = type(str("%sAdmin" % model.__name__), (admin_class,), options)

				# Instantiate the admin class to save in the registry
				self._registry_avs.setdefault(model, []).insert(0, admin_class)

	def unregister(self, model_or_iterable):
		"""
		Unregisters the given model(s).

		If a model isn't already registered, this will raise NotRegistered.
		"""
		from xadmin.views.base import BaseAdminView
		if isinstance(model_or_iterable, (ModelBase, BaseAdminView)):
			model_or_iterable = [model_or_iterable]
		for model in model_or_iterable:
			if isinstance(model, ModelBase):
				if model not in self._registry:
					raise NotRegistered('The model %s is not registered' % model.__name__)
				del self._registry[model]
			else:
				if model not in self._registry_avs:
					raise NotRegistered('The admin_view_class %s is not registered' % model.__name__)
				del self._registry_avs[model]

	def set_loginview(self, login_view):
		self.login_view = login_view

	def has_permission(self, request):
		"""
		Returns True if the given HttpRequest has permission to view
		*at least one* page in the admin site.
		"""
		return request.user.is_active and request.user.is_staff

	def check_dependencies(self):
		"""
		Check that all things needed to run the admin have been correctly installed.

		The default implementation checks that LogEntry, ContentType and the
		auth context processor are installed.
		"""
		from django.apps import apps

		if not apps.is_installed("django.contrib.contenttypes"):
			raise ImproperlyConfigured("Put 'django.contrib.contenttypes' in "
			                           "your INSTALLED_APPS setting in order to use the admin application.")

		default_template_engine = Engine.get_default()
		if not ('django.contrib.auth.context_processors.auth' in default_template_engine.context_processors or
		        'django.core.context_processors.auth' in default_template_engine.context_processors):
			raise ImproperlyConfigured("Put 'django.contrib.auth.context_processors.auth' "
			                           "in your TEMPLATE_CONTEXT_PROCESSORS setting in order to use the admin application.")

	def admin_view(self, view, cacheable=False):
		"""
		Decorator to create an admin view attached to this ``AdminSite``. This
		wraps the view and provides permission checking by calling
		``self.has_permission``.

		You'll want to use this from within ``AdminSite.get_urls()``:

			class MyAdminSite(AdminSite):

				def get_urls(self):
					from django.conf.urls import url

					urls = super(MyAdminSite, self).get_urls()
					urls += [
						url(r'^my_view/$', self.admin_view(some_view))
					]
					return urls

		By default, admin_views are marked non-cacheable using the
		``never_cache`` decorator. If the view can be safely cached, set
		cacheable=True.
		"""

		def inner(request, *args, **kwargs):
			if not self.has_permission(request) and getattr(view, 'need_site_permission', True):
				return self.create_admin_view(self.login_view)(request, *args, **kwargs)
			return view(request, *args, **kwargs)

		if not cacheable:
			inner = never_cache(inner)
		return update_wrapper(inner, view)

	def _get_merge_attrs(self, option_class, plugin_class):
		attrs = {}
		options = self._admin_plugins_cache.get(option_class)
		if options is None:
			# optimizes execution by excluding everything that is protected and private from the list and caches
			options = set([name for name in dir(option_class) if name[0] != '_'])
			self._admin_plugins_cache[option_class] = options
		for name in options:
			if not hasattr(plugin_class, name):
				continue
			attr = getattr(option_class, name)
			# accepts configuration methods and classes.
			if not callable(attr) or inspect.isclass(attr):
				attrs[name] = attr
		return attrs

	def _get_settings_class(self, view_class):
		name = view_class.__name__.lower()

		if name in self._registry_settings:
			return self._registry_settings[name]
		elif name.endswith('admin') and name[0:-5] in self._registry_settings:
			return self._registry_settings[name[0:-5]]
		elif name.endswith('adminview') and name[0:-9] in self._registry_settings:
			return self._registry_settings[name[0:-9]]

		return None

	def _create_plugin(self, option_classes):
		def merge_class(plugin_class):
			if option_classes:
				attrs = {}
				bases = [plugin_class]
				plugin_class_name = plugin_class.__name__
				meta_class_names = (plugin_class_name,
				                    plugin_class_name.replace('Plugin', ''))
				for oc in option_classes:
					attrs.update(self._get_merge_attrs(oc, plugin_class))
					for meta_name in meta_class_names:
						if meta_class := getattr(oc, meta_name, None):
							bases.insert(0, meta_class)
				if attrs:
					if (metaclasse := type(plugin_class)) is not type:
						# fix: metaclass conflict
						metaclasses = (metaclasse, MergeAdminMetaclass)
						metaclasse = type(''.join([m.__name__ for m in metaclasses]), metaclasses, {})
					else:
						metaclasse = MergeAdminMetaclass
					plugin_class = metaclasse(
						'%s%s' % (''.join([oc.__name__ for oc in option_classes]), plugin_class_name),
						tuple(bases), attrs)
			return plugin_class

		return merge_class

	def get_plugins(self, admin_view_class, *option_classes):
		"""Extrai os plugins registrados na hierarquia de views"""
		from xadmin.views import BaseAdminView
		plugins = []
		# option classes affect all plugins but the impact of this is mitigated by name caching
		option_classes = [oc for oc in option_classes if oc]
		for klass in admin_view_class.mro()[:-1]:  # exclude object
			klass_options = []
			if klass == BaseAdminView or issubclass(klass, BaseAdminView):
				reg_avs_class = self._registry_avs.get(klass)
				if reg_avs_class:
					klass_options.extend(reg_avs_class)
				settings_class = self._get_settings_class(klass)
				if settings_class:
					klass_options.append(settings_class)
				plugins_class = self._registry_plugins.get(klass, ())
				# update option history
				option_classes.extend(klass_options)
				if plugins_class:
					# will extract the common options in reverse order
					plugin_cls_opts = option_classes[::-1]
					merge_func = self._create_plugin(plugin_cls_opts)
					for plugin_class in plugins_class:
						plugins.append(merge_func(plugin_class))
		return plugins

	def get_view_class(self, view_class, option_class=None, **opts):
		plugins_options = [option_class] if option_class else []
		merges = [option_class] if option_class else []
		for klass in view_class.mro()[:-1]:  # exclude object
			reg_avs_class = self._registry_avs.get(klass)
			if reg_avs_class:
				plugins_options.extend(reg_avs_class)
				merges.extend(reg_avs_class)
			settings_class = self._get_settings_class(klass)
			if settings_class:
				merges.append(settings_class)
			merges.append(klass)
		merge_class_name = ''.join([c.__name__ for c in merges])
		if (view_class_merge := self._admin_view_cache.get(merge_class_name)) is None:
			plugins = self.get_plugins(view_class, *plugins_options)
			self._admin_view_cache[merge_class_name] = view_class_merge = MergeAdminMetaclass(
				f"{view_class.__name__}Merge{len(merges)}", tuple(merges),
				dict({'admin_site': self,
				      'plugin_classes': plugins,
				      'admin_view_class': view_class,
				      'admin_merge_class_name': merge_class_name
				      },
				     **opts)
			)
		return view_class_merge

	def create_admin_view(self, admin_view_class, initargs=None, initkwargs=None):
		view_class = self.get_view_class(admin_view_class)
		return view_class.as_view(*(initargs or ()), **(initkwargs or {}))

	def create_model_admin_view(self, admin_view_class, model, option_class, initargs=None, initkwargs=None):
		view_class = self.get_view_class(admin_view_class, option_class)
		return view_class.as_view(*(initargs or ()), **(initkwargs or {}))

	def wrap_view(self, view, cacheable=False):
		"""View that passes through admin permissions"""

		def wrapper(*args, **kwargs):
			return self.admin_view(view, cacheable)(*args, **kwargs)

		wrapper.admin_site = self
		return update_wrapper(wrapper, view)

	def _get_nested_urls(self, registry_views: list, base_view_class):
		"""Registered sites views"""
		# permission check
		wrap = self.wrap_view
		urlpatterns = []

		# sort the types (AdminUrl, AdminPath)
		registry_views.sort(reverse=True)

		tuple_list = (tuple, list)
		for view_spec in registry_views:
			if isinstance(view_spec.cls_func, tuple_list):
				# Registering urls in a namespace
				view_urls = []
				for url in view_spec.cls_func:
					if isinstance(url, tuple_list):
						url = AdminUrl(*url)
					elif not isinstance(url, AdminUrl):
						url = AdminUrl(None, url)
					# converte as class view para instance view
					if inspect.isclass(url.cls_func) and issubclass(url.cls_func, base_view_class):
						view = wrap(self.create_admin_view(url.cls_func, initargs=url.initargs,
						                                   initkwargs=url.initkwargs),
						            cacheable=url.cacheable)
					elif isinstance(url, AdminUrl) and not callable(url.cls_func):
						# esse caso representa urls dentro de urls indefinidamente
						nested_urls = self._get_nested_urls([url], base_view_class)
						view_urls.extend(nested_urls)
						continue
					else:
						# hardcore: a view é uma função que cria suas próprias urls
						try:
							view = include(url.cls_func(self))
						except TypeError as exc:
							raise ImproperlyConfigured(f"admin view include {url.cls_func}\n{exc}")
					view_urls.append(url(view))
				# guarda o conjunto de urls no namespace
				urlpatterns.append(view_spec.include(view_urls))
				continue
			elif inspect.isclass(view_spec.cls_func) and issubclass(view_spec.cls_func, base_view_class):
				view = wrap(self.create_admin_view(view_spec.cls_func, initargs=view_spec.initargs,
				                                   initkwargs=view_spec.initkwargs),
				            cacheable=view_spec.cacheable)
			else:
				# hardcore: a view é uma função que cria suas próprias urls
				try:
					view = include(view_spec.cls_func(self))
				except TypeError as exc:
					raise ImproperlyConfigured(f"admin view include {view_spec.cls_func}\n{exc}")
			urlpatterns.append(view_spec(view))
		return urlpatterns

	def get_urls(self):
		from xadmin.views.base import BaseAdminView

		# permission check
		wrap = self.wrap_view

		# Admin-hidra-wide views.
		urlpatterns = self._get_nested_urls(self._registry_views, BaseAdminView)
		urlpatterns.append(
			dj_path('jsi18n/', wrap(self.i18n_javascript, cacheable=True), name='jsi18n')
		)
		# Add in each model's views.
		for model, admin_class in self._registry.items():
			opts = model._meta
			model_urlpatterns = []
			for view_spec in self._registry_modelviews:
				model_admin_view = self.create_model_admin_view(
					view_spec.cls_func, model, admin_class,
					initargs=view_spec.initargs,
					initkwargs=view_spec.initkwargs
				)
				model_wrapped_view = wrap(model_admin_view, cacheable=view_spec.cacheable)
				name = view_spec.name % (opts.app_label, opts.model_name)
				model_urlpatterns.append(view_spec(model_wrapped_view, route=view_spec.route, name=name))
			if (route := getattr(admin_class, 'admin_path', None)) is None:
				urlpatterns.append(
					re_path(r'^%s/%s/' % (opts.app_label, opts.model_name), include(model_urlpatterns))
				)
			elif isinstance(route, AdminRoute):
				urlpatterns += [route(model_urlpatterns)]
		# remove optimization cache from building plugins
		self._admin_plugins_cache.clear()
		return urlpatterns

	@property
	def urls(self):
		return self.get_urls(), self.name, self.app_name

	def i18n_javascript(self, request):
		"""
		Displays the i18n JavaScript that the Django admin requires.

		This takes into account the USE_I18N setting. If it's set to False, the
		generated JavaScript will be leaner and faster.
		"""
		from django.views.i18n import JavaScriptCatalog
		# Gives plugins the ability to add your translation scripts.
		packages = getattr(settings, 'XADMIN_I18N_JAVASCRIPT_PACKAGES', [])
		try:
			packages.extend(['django.contrib.admin',
			                 'xadmin'])
		except AttributeError:
			raise ImproperlyConfigured('Expected list type as attribute '
			                           'in "XADMIN_I18N_JAVASCRIPT_PACKAGES"')
		return JavaScriptCatalog.as_view(packages=packages)(request)

	def init(self):
		if site.ready:
			raise ImproperlyConfigured(f"Admin site already configured!")
		# convert lists of options into a single class.
		for model in list(self._registry):
			self._registry[model] = self._registry[model].resolve()

	# Disables login to script translations.
	i18n_javascript.need_site_permission = False


# This global object represents the default admin site, for the common case.
# You can instantiate AdminSite in your own code to create a custom admin site.
site = AdminSite()


def register(models, **kwargs):
	def _model_admin_wrapper(admin_class):
		site.register(models, admin_class)
		return admin_class
	return _model_admin_wrapper
