# -*-coding:utf-8-*-
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
from .views import wechat, createMenu, getMenu, deleteMenu, pay_notify, OrderPayView, RegisterView, PersonInfoView, \
    OrderRemoveView, ScanQRCodeView, UserDetailView, UserBalanceView, UserCollectionView

urlpatterns = [
    url(r'^$', wechat),  # 微信入口
    url(r'^createmenu/$', createMenu, name="wxchat-create-menu"),
    url(r'^getmenu/$', getMenu, name="wxchat-get-menu"),
    url(r'^delmenu/$', deleteMenu, name="wxchat-delete-menu"),
    # url(r'^pay/orderpay$', OrderPayView.as_view(), name='wxchat-order-pay'),    # 微信充值
    url(r'^scanqrcode/$', ScanQRCodeView.as_view(), name='wxchat-scanqrcode'),
    url(r'^register/$', RegisterView.as_view(), name='wxchat-register'),
    url(r'^personinfo/$', PersonInfoView.as_view(), name='wxchat-personinfo'),
    url(r'^userdetail/(?P<id>\d+)/$', UserDetailView.as_view(), name='wxchat-user-detail'),
    url(r'^balance/(?P<id>\d+)/$', UserBalanceView.as_view(), name='wxchat-balance-detail'),
    url(r'^orderdel/$', OrderRemoveView.as_view(), name='wxchat-order-remove'),
    url(r'^mycollection/$', UserCollectionView.as_view(), name='wxchat-my-collection'),
]
