# -*-coding:utf-8-*-
from django.conf.urls import url

from .views import ApplyRefund

urlpatterns = [
    url(r'^apply_refund/$', ApplyRefund.as_view(), name='wxchat-apply-refund'),
]