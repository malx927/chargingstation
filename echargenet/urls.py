# coding=utf-8
from django.conf.urls import url, include
from django.conf import settings
# from django.contrib import admin
from django.views.generic import TemplateView
from .views import *

urlpatterns = [
   url(r'^query_token', ObtainAuthToken.as_view(), name='query-token'),
   url(r'^query_stations_info$', StationInfoListAPIView.as_view(), name='station-info-list'),
   url(r'^query_station_status$', StationStatusListAPIView.as_view(), name='station-status-list'),
   url(r'^query_equip_auth', EquipAuthAPIView.as_view(), name='query-equip-auth'),
   url(r'^query_start_charge', StartChargeAPIView.as_view(), name='query-start-charge'),
   url(r'^query_stop_charge', StopChargeAPIView.as_view(), name='query-stop-charge'),
   url(r'^query_equip_charge_status', EquipChargeStatusAPIView.as_view(), name='query-equip-charge-status'),
   url(r'^query_station_stats', StationStatsAPIView.as_view(), name='query-station-stats'),
   url(r'^query_equip_business_policy', EquipBusinessPolicyAPIView.as_view(), name='query-equip-business-policy'),

]
