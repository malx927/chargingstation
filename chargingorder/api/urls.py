#-*-coding:utf-8-*-
from django.conf.urls import url

from chargingorder.api.views import OrderDayStats
from stationmanager.api.views import ChargingPileListAPIView, AreaCodeListAPIView

__author__ = 'malixin'


urlpatterns = [
    url(r'^account_balance/$', ChargingPileListAPIView.as_view(), name='charging-pile-list'),
    url(r'^areacodelist/$', AreaCodeListAPIView.as_view(), name='area-code-list'),
    url(r'^orderdaystats/$', OrderDayStats.as_view(), name='order-day-stats'),
]

