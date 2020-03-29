import datetime
import logging
import time
import json

from django.db.models import Sum, Count, F, Case, When, IntegerField, FloatField
from rest_framework.response import Response
from rest_framework.views import APIView
from chargingorder.models import Order, OrderChargDetail
from django.db import connection
from django_redis import get_redis_connection
# 累计充电次数
# 累计充电电量
# 实时充电总功率
# 充电桩总数
from stationmanager.models import ChargingPile
from statistic.tasks import charging_yesterday_data, charging_device_stats, charging_accumulative_total_stats, \
    current_month_year_accumlative_stats, real_time_power_stats, charging_today_data

logger = logging.getLogger("django")


class BigScreenChargStatsAPIView(APIView):
    """累计充电次数、累计充电电量、充电桩总数"""
    def get(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        accum_readings = conn.get("yd_accum_readings")
        if accum_readings is None:
            charging_accumulative_total_stats()
            time.sleep(0.5)
            accum_readings = conn.get("yd_accum_readings")

        accum_counts = conn.get("yd_accum_counts")
        # accum_fees = conn.get("yd_accum_fees")
        device_counts = conn.get("yd_device_counts")

        results = dict()
        results["accum_readings"] = accum_readings
        results["accum_counts"] = accum_counts
        results["device_counts"] = device_counts
        logger.info(results)
        return Response(results)


class BigScreenRealtimePowerAPIView(APIView):
    """"实时充电功率"""
    def get(self, request, *args, **kwargs):
        logger.info("Enter BigScreenRealtimePowerAPIView")
        conn = get_redis_connection("default")
        results_stats = conn.get("yd_real_time_power_stats")
        if results_stats is None:
            print("---------------")
            real_time_power_stats()
            time.sleep(0.5)
            results_stats = conn.get("yd_real_time_power_stats")

        results = dict()
        logger.info("Leave BigScreenRealtimePowerAPIView")
        results["realtime_power"] = results_stats
        return Response(results)


class BigScreenDeviceStatsAPIView(APIView):
    """充电桩分类统计"""
    def get(self, request, *args, **kwargs):
        logger.info("Enter BigScreenDeviceStatsAPIView")
        conn = get_redis_connection("default")
        results_stats = conn.get("yd_device_category_stats")
        if results_stats is None:
            charging_device_stats()
            print("++++++++++++++++")
            time.sleep(0.5)
            results_stats = conn.get("yd_device_category_stats")

        results = json.loads(results_stats.decode("utf-8"))
        logger.info(results)

        return Response(results)


class TodayChargingCountAPIView(APIView):
    """今日充电次数"""
    def get(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        # 今天合计数据
        today_total_counts = conn.get("yd_today_total_counts")
        if today_total_counts is None:
            today_total_counts = 0

        # 今天分时数据
        today_hour_count = conn.hgetall("yd_today_hour_count")
        # 昨天分时数据
        yesterday_hour_count = conn.hgetall("yd_yesterday_hour_count")

        data = {
            "total_count": today_total_counts,
            "today_count": list(today_hour_count.values()),
            "yesterday_count": list(yesterday_hour_count.values()),
            "hour_list": list(yesterday_hour_count.keys()),
        }
        logger.info(data)
        return Response(data)


class TodayChargingReadingsAPIView(APIView):
    """今日充电量"""
    def get(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        # 今天合计数据
        today_total_readings = conn.get("yd_today_total_readings")
        if today_total_readings is None:
            today_total_readings = 0

        # 今天分时数据
        today_hour_readings = conn.hgetall("yd_today_hour_readings")
        # 昨天分时数据
        yesterday_hour_readings = conn.hgetall("yd_yesterday_hour_readings")

        data = {
            "total_readings": today_total_readings,
            "today_readings": list(today_hour_readings.values()),
            "yesterday_readings": list(yesterday_hour_readings.values()),
            "hour_list": list(yesterday_hour_readings.keys()),
        }
        return Response(data)


class TodayChargingMoneyAPIView(APIView):
    """今日充电金额"""
    def get(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        # 今天合计数据
        today_total_money = conn.get("yd_today_total_money")
        if today_total_money is None:
            today_total_money = 0
        # 今天分时数据
        today_hour_money = conn.hgetall("yd_today_hour_money")
        # 昨天分时数据
        yesterday_hour_money = conn.hgetall("yd_yesterday_hour_money")

        data = {
            "total_money": today_total_money,
            "today_money": list(today_hour_money.values()),
            "yesterday_money": list(yesterday_hour_money.values()),
            "hour_list": list(yesterday_hour_money.keys()),
        }
        return Response(data)


class TodayChargingPowerAPIView(APIView):
    """今日充电电力"""
    def get(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        # 今天合计数据
        today_total_power = conn.get("yd_today_total_power")
        if today_total_power is None:
            today_total_power = 0

        # 今天分时数据
        today_hour_power = conn.hgetall("yd_today_hour_power")
        # 昨天分时数据
        yesterday_hour_power = conn.hgetall("yd_yesterday_hour_power")
        data = {
            "total_power": today_total_power,
            "today_power": list(today_hour_power.values()),
            "yesterday_power": list(yesterday_hour_power.values()),
            "hour_list": list(yesterday_hour_power.keys()),
        }
        return Response(data)


class CurrentMonthYearAccumAPIView(APIView):
    """当前月、年金额统计"""
    def get(self, request, *args, **kwargs):
        conn = get_redis_connection("default")
        results = conn.get("yd_current_mon_year_accum_stats")
        if results is None:
            current_month_year_accumlative_stats()
            time.sleep(0.5)
            results = conn.get("yd_current_mon_year_accum_stats")

        result_dict = json.loads(results.decode("utf-8"))
        logger.info(result_dict)
        return Response(result_dict)

