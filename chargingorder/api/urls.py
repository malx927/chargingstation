#-*-coding:utf-8-*-
from django.conf.urls import url

from chargingorder.api.views import OrderDayStats, OrderMonthStats, OrderYearStats, OrderCategoryStats, \
    OrderDayAnalysis, OrderMonthAnalysis, OrderYearAnalysis
from stationmanager.api.views import ChargingPileListAPIView, AreaCodeListAPIView

__author__ = 'malixin'


urlpatterns = [
    url(r'^account_balance/$', ChargingPileListAPIView.as_view(), name='charging-pile-list'),
    url(r'^areacodelist/$', AreaCodeListAPIView.as_view(), name='area-code-list'),
    url(r'^orderdaystats/$', OrderDayStats.as_view(), name='order-day-stats'),
    url(r'^ordermonthstats/$', OrderMonthStats.as_view(), name='order-month-stats'),
    url(r'^orderyearstats/$', OrderYearStats.as_view(), name='order-year-stats'),
    url(r'^ordercategorystats/$', OrderCategoryStats.as_view(), name='order-category-stats'),
    url(r'^order-day-analysis/$', OrderDayAnalysis.as_view(), name='order-day-analysis'),
    url(r'^order-month-analysis/$', OrderMonthAnalysis.as_view(), name='order-month-analysis'),
    url(r'^order-year-analysis/$', OrderYearAnalysis.as_view(), name='order-year-analysis'),
]

