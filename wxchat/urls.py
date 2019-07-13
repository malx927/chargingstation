# -*-coding:utf-8-*-
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
# from django.contrib import admin
from django.views.generic import TemplateView
from .views import wechat, createMenu, getMenu, deleteMenu, pay_notify, OrderPayView, RegisterView, PersonInfoView, \
    OrderRemoveView

urlpatterns = [
    url(r'^$', wechat),  # 微信入口
    url(r'^createmenu/$', createMenu, name="wxchat-create-menu"),
    url(r'^getmenu/$', getMenu, name="wxchat-get-menu"),
    url(r'^delmenu/$', deleteMenu, name="wxchat-delete-menu"),
    # url(r'^pay/orderpay$', OrderPayView.as_view(), name='wxchat-order-pay'),    # 微信充值
    # url(r'^pay/notify/$', pay_notify, name='wxchat-notify'),
    url(r'^register/$', RegisterView.as_view(), name='wxchat-register'),
    url(r'^personinfo/$', PersonInfoView.as_view(), name='wxchat-personinfo'),
    url(r'^orderdel/$', OrderRemoveView.as_view(), name='wxchat-order-remove'),
]
