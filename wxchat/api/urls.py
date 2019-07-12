#-*-coding:utf-8-*-
from django.conf.urls import url
from stationmanager.api.views import ChargingPileListAPIView, AreaCodeListAPIView
from wxchat.api.views import UserInfoRetrieveAPIView

__author__ = 'malixin'


urlpatterns = [
    url(r'^account_balance/(?P<openid>[\w-]+)/$', UserInfoRetrieveAPIView.as_view(), name='wechat-api-account-balance'),
]

