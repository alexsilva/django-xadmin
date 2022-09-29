# coding=utf-8
from django.urls import path

# Uncomment the next two lines to enable the admin:
import xadmin

xadmin.autodiscover()

# version模块自动注册需要版本控制的 Model
from xadmin.plugins import xversion

xversion.register_models()

urlpatterns = [
	path(r'', xadmin.site.urls)
]
