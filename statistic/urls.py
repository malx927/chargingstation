from django.conf.urls import url
from django.views.generic import TemplateView

from statistic.views import BigScreenChargStatsAPIView, BigScreenRealtimePowerAPIView, BigScreenDeviceStatsAPIView, \
   TodayChargingCountAPIView, TodayChargingReadingsAPIView, TodayChargingMoneyAPIView, TodayChargingPowerAPIView, \
   CurrentMonthYearAccumAPIView

urlpatterns = [
   url(r'^big_charging_stats/$', BigScreenChargStatsAPIView.as_view(), name='big-screen-charg-stats'),
   url(r'^big_realtime_power/$', BigScreenRealtimePowerAPIView.as_view(), name='big-screen-realtime-power'),
   url(r'^big_device_stats/$', BigScreenDeviceStatsAPIView.as_view(), name='big-screen-device-stats'),
   url(r'^big_today_count_stats/$', TodayChargingCountAPIView.as_view(), name='big-today-count-stats'),
   url(r'^big_today_readings_stats/$', TodayChargingReadingsAPIView.as_view(), name='big-today-readings-stats'),
   url(r'^big_today_money_stats/$', TodayChargingMoneyAPIView.as_view(), name='big-today-money-stats'),
   url(r'^big_today_power_stats/$', TodayChargingPowerAPIView.as_view(), name='big-today-power-stats'),
   url(r'^bigscreen/$', TemplateView.as_view(template_name="statistic/bigscreen.html")),
   url(r'^big_current_month_year_stats/$', CurrentMonthYearAccumAPIView.as_view(), name='big-current-month-year-stats'),
]
