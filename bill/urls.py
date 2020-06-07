# -*-coding:utf-8-*-
from django.conf.urls import url

from .views import ApplyRefundView, ApplyRefundListView, RefundView

urlpatterns = [
    url(r'^apply_refund/$', ApplyRefundView.as_view(), name='wxchat-apply-refund'),
    url(r'^apply_refund_list/$', ApplyRefundListView.as_view(), name='wxchat-apply-refund-list'),
    url(r'^refund/$', RefundView.as_view(), name='wxchat-refund'),
]