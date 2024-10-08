from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as logout
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from xadmin.forms import AdminAuthenticationForm
from xadmin.layout import FormHelper
from xadmin.models import UserSettings
from xadmin.views.base import BaseAdminView, filter_hook
from xadmin.views.dashboard import Dashboard


class IndexView(Dashboard):
	title = _("Main Dashboard")
	icon = "fa fa-tachometer-alt"

	def get_page_id(self):
		return 'home'


class UserSettingView(BaseAdminView):

	@method_decorator(never_cache)
	def post(self, request):
		key = request.POST['key']
		val = request.POST['value']
		us, created = UserSettings.objects.get_or_create(
			user=self.user, key=key)
		us.value = val
		us.save()
		return HttpResponse('')


class AuthBaseAdminView(BaseAdminView):
	title = None

	def get_context(self):
		context = super().get_context()
		context['title'] = self.title
		return context


class LoginView(AuthBaseAdminView, AuthLoginView):
	title = _("Please Login")
	login_form = AdminAuthenticationForm
	authentication_form = None
	login_template = None
	redirect_authenticated_user = True

	def dispatch(self, request, *args, **kwargs):
		# Ensures the logged in user still has permission to access admin views.
		# Not validating this results in recursion of redirects.
		self.redirect_authenticated_user &= bool(self.admin_site.has_permission(self.request))
		return super().dispatch(request, *args, **kwargs)

	@filter_hook
	def get_form_class(self):
		return self.authentication_form or self.login_form

	@filter_hook
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		helper = self.get_form_helper()
		# view context default
		ctx = self.get_context()
		context.update(ctx, **{
			'helper': helper,
			'app_path': self.request.get_full_path(),
			REDIRECT_FIELD_NAME: self.request.get_full_path()
		})
		return context

	@filter_hook
	def get_template_names(self):
		return [self.login_template or 'xadmin/views/login.html']

	@filter_hook
	def get_form_helper(self):
		helper = FormHelper()
		helper.form_tag = False
		helper.use_custom_control = False
		helper.include_media = False
		return helper

	@filter_hook
	def form_valid(self, form):
		return super().form_valid(form)

	@filter_hook
	def form_invalid(self, form):
		return super().form_invalid(form)

	@filter_hook
	def get_form_kwargs(self):
		return super().get_form_kwargs()

	@filter_hook
	def get_success_url(self):
		url = self.get_redirect_url()
		# Using LOGIN_REDIRECT_URL will not always have the expected behavior in administration.
		return url or self.get_admin_url("index")

	@filter_hook
	def get_redirect_url(self):
		return super().get_redirect_url()

	@filter_hook
	def get_form(self, **kwargs):
		return super().get_form(**kwargs)

	@method_decorator(never_cache)
	@filter_hook
	def get(self, request, *args, **kwargs):
		return super().get(request, *args, **kwargs)

	@method_decorator(never_cache)
	@filter_hook
	def post(self, request, *args, **kwargs):
		return super().post(request, *args, **kwargs)


class LogoutView(AuthBaseAdminView):
	title = _("Logout Success")

	logout_template = None
	need_site_permission = False

	@filter_hook
	def update_params(self, defaults):
		pass

	@method_decorator(never_cache)
	def get(self, request, *args, **kwargs):
		context = self.get_context()
		defaults = {
			'extra_context': context,
			# 'current_app': self.admin_site.name,
			'template_name': self.logout_template or 'xadmin/views/logged_out.html',
		}
		if self.logout_template is not None:
			defaults['template_name'] = self.logout_template

		self.update_params(defaults)
		# return logout(request, **defaults)
		return logout.as_view(**defaults)(request)

	@method_decorator(never_cache)
	def post(self, request, *args, **kwargs):
		return self.get(request)
