#-*-coding:utf-8-*-
from django.conf.urls import url
from stationmanager.api.views import ChargingPileListAPIView, AreaCodeListAPIView

__author__ = 'malixin'


urlpatterns = [
    url(r'^pilelist/$', ChargingPileListAPIView.as_view(), name='charging-pile-list'),
    url(r'^areacodelist/$', AreaCodeListAPIView.as_view(), name='area-code-list'),
]

