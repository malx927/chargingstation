# coding=utf-8
from django.conf.urls import url, include

from django.views.generic import TemplateView
from wxchat.views import OrderPayView, pay_notify

from .views import *

urlpatterns = [
   # url(r'^$', index, name='order-index'),
   # url(r'^prepay/(?P<pile_sn>[\w-]+)/(?P<gun_num>\d+)/$', RechargeView.as_view(), name='order-prepay'),
   # url(r'^recharge/$', RechargeView.as_view(), name='order-recharge'),
   # url(r'^recharge_order_status/$', RechargeOrderStatusView.as_view(), name='order-recharge-status'),
   # url(r'^errors/$', TemplateView.as_view(template_name='chargingorder/charging_pile_status.html'), name='order-errors'),
   # url(r'^pay/orderpay$', OrderPayView.as_view(), name='wxchat-order-pay'),    # 微信充值
   # url(r'^pay/notify/$', pay_notify, name='wxchat-notify'),
   # url(r'chargestop/$', OrderChargeStopView.as_view(), name='order-charge-stop'),
   # url(r'orderlist/$', OrderView.as_view(), name='user-order-list'),
   # url(r'orderdetail/(?P<pk>\d+)/$', OrderDetailView.as_view(), name='user-order-detail'),
   # url(r'charging_track/$', ChargingTrackListView.as_view(), name='charging-track-list'),

]
