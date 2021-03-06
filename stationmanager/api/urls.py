#-*-coding:utf-8-*-
from django.conf.urls import url

from stationmanager.api.views import ChargingPileListAPIView, AreaCodeListAPIView, StationStatsView, StationListAPIView

__author__ = 'malixin'


urlpatterns = [
    url(r'^pilelist/$', ChargingPileListAPIView.as_view(), name='charging-pile-list'),
    url(r'^areacodelist/$', AreaCodeListAPIView.as_view(), name='area-code-list'),
    url(r'^stationstats/$', StationStatsView.as_view(), name='station-stats'),
    url(r'^stationlist/$', StationListAPIView.as_view(), name='station-list'),
]

