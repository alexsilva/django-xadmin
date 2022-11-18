from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy, ugettext as _

ERROR_MESSAGE = ugettext_lazy(
	"Please enter the correct username and password "
	"for a staff account. Note that both fields are case-sensitive."
)


class AdminAuthenticationForm(AuthenticationForm):
	"""
	A custom authentication form used in the admin app.

	"""
	this_is_the_login_form = forms.BooleanField(
		widget=forms.HiddenInput,
		initial=1,
		error_messages={
			'required': ugettext_lazy("Please log in again, because your session has expired.")
		})

	def confirm_login_allowed(self, user):
		if not user.is_staff:
			raise self.get_invalid_login_error()
		return super().confirm_login_allowed(user)
