# -*-coding:utf-8-*-
from django.conf.urls import url
from wxchat.api.views import UserInfoRetrieveAPIView, UserCollectionAPIView, BalanceResetAPIView

__author__ = 'malixin'


urlpatterns = [
    url(r'^account_balance/(?P<openid>[\w-]+)/$', UserInfoRetrieveAPIView.as_view(), name='wechat-api-account-balance'),
    url(r'^user_collection/$', UserCollectionAPIView.as_view(), name='wechat-api-user-collection'),
    url(r'^balance_reset/$', BalanceResetAPIView.as_view(), name='wechat-api-balance-reset'),
]

