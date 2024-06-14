from functools import partial

from django.test.client import RequestFactory


def is_ajax(request):
	"""django:4+"""
	return request.headers.get('x-requested-with') == 'XMLHttpRequest'


class RequestAdminFactory(RequestFactory):

	def request(self, **request):
		req = super().request(**request)
		req.is_ajax = partial(is_ajax, req)
		return req
