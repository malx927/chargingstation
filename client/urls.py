# -*-coding:utf-8-*-
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
from .views import index
urlpatterns = [
    url(r'^$', index),  # 客户端入口

]
