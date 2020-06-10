# -*-coding:utf-8-*-
from django.conf.urls import url

from .views import ApplyRefundView, ApplyRefundListView, RefundView, UserUnfreezeView, InvoiceTitleView, \
    InvoiceTitleDetailView

urlpatterns = [
    url(r'^apply_refund/$', ApplyRefundView.as_view(), name='wxchat-apply-refund'),
    url(r'^apply_refund_list/$', ApplyRefundListView.as_view(), name='wxchat-apply-refund-list'),
    url(r'^refund/$', RefundView.as_view(), name='wxchat-refund'),
    url(r'^unfreeze/$', UserUnfreezeView.as_view(), name='wxchat-user-unfreeze'),
    url(r'^invoice/$', InvoiceTitleView.as_view(), name='invoice-title'),
    url(r'^invoice_detail/(?P<pk>\d+)$', InvoiceTitleDetailView.as_view(), name='invoice-title-detail'),
]