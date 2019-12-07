# -*-coding:utf-8-*-
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
from .views import index, login

urlpatterns = [
    url(r'^$', index, name="index"),  # 客户端入口
    url(r'^login/$', login, name="login"),  # 登录窗口

]
