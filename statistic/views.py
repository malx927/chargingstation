import datetime

from django.db.models import Sum, Count, F, Case, When, IntegerField
from rest_framework.response import Response
from rest_framework.views import APIView
from chargingorder.models import Order
from django.db import connection

# 累计充电次数
# 累计充电电量
# 实时充电总功率
# 充电桩总数
from stationmanager.models import ChargingPile


class BigScreenChargStatsAPIView(APIView):
    """大累计充电次数、累计充电电量、充电桩总数"""
    def get(self, request, *args, **kwargs):
        results = Order.objects.filter(status=2, pay_time__isnull=False, cash_fee__gt=0).\
            aggregate(accum_readings=Sum("total_readings"), accum_counts=Count("id"), accum_fees=Sum("cash_fee"))

        device_counts = ChargingPile.objects.count()

        results["accum_readings"] = 0.00 if results["accum_readings"] is None else results["accum_readings"]
        results["accum_fees"] = 0.00 if results["accum_fees"] is None else results["accum_fees"]
        results["device_counts"] = device_counts
        return Response(results)


class BigScreenRealtimePowerAPIView(APIView):
    """"实时充电功率"""
    def get(self, request, *args, **kwargs):
        results = Order.objects.filter(status__in=[0, 1]). \
            aggregate(realtime_power=Sum(F("output_voltage") * F("output_current"))/1000)
        results["realtime_power"] = 0 if results["realtime_power"] is None else results["realtime_power"]
        return Response(results)


class BigScreenDeviceStatsAPIView(APIView):
    """充电桩分类统计"""
    def get(self, request, *args, **kwargs):
        results = ChargingPile.objects.select_related("station").values("station", "station__name").\
            order_by("station").annotate(
            dc_device=Sum(Case(When(pile_type__in=[1, 2], then=1), default=0, output_field=IntegerField())),
            ac_device=Sum(Case(When(pile_type__in=[5, 6], then=1), default=0, output_field=IntegerField())),
        )
        return Response(results)


class TodayChargingCountAPIView(APIView):
    """今日充电次数"""
    def get(self, request, *args, **kwargs):
        cur_date = datetime.datetime.now().date()
        cur_hour = datetime.datetime.now().hour + 1
        # 今天合计数据
        total_results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=cur_date).count()
        # 今天分时数据
        today_results = self.get_hour_data(cur_date, cur_hour)
        # 昨天分时数据
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        yesterday = yesterday.date()
        yesterday_results = self.get_hour_data(yesterday)
        data = {
            "total_count": total_results,
            "today_count": list(today_results.values()),
            "yesterday_count": list(yesterday_results.values()),
            "hour_list": list(yesterday_results.keys()),
        }
        return Response(data)

    def get_hour_data(self, current_date, limit_hour=24):
        """分时统计数据"""
        results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=current_date)\
            .extra(select={'hour': "HOUR(begin_time)"})\
            .values("hour").annotate(count=Count("id")).order_by("hour")
        dict_results = {k: 0 for k in range(limit_hour)}
        for item in results:
            key = item["hour"]
            dict_results[key] = item["count"]
        return dict_results


class TodayChargingReadingsAPIView(APIView):
    """今日充电量"""
    def get(self, request, *args, **kwargs):
        cur_date = datetime.datetime.now().date()
        cur_hour = datetime.datetime.now().hour + 1
        # 今天合计数据
        total_results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=cur_date)\
            .aggregate(total_readings=Sum("total_readings"))
        # 今天分时数据
        today_results = self.get_hour_readings_data(cur_date, cur_hour)
        # 昨天分时数据
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        yesterday = yesterday.date()
        yesterday_results = self.get_hour_readings_data(yesterday)
        data = {
            "total_readings": total_results.get("total_readings", 0),
            "today_readings": today_results,
            "yesterday_readings": yesterday_results,
        }
        return Response(data)

    def get_hour_readings_data(self, current_date, limit_hour=24):
        """分时统计数据"""
        results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=current_date)\
            .extra(select={'hour': "HOUR(begin_time)"})\
            .values("hour").annotate(readings=Sum("total_readings")).order_by("hour")
        dict_results = {k: 0 for k in range(limit_hour)}
        for item in results:
            key = item["hour"]
            dict_results[key] = item["readings"]
        return dict_results


class TodayChargingMoneyAPIView(APIView):
    """今日充电金额"""
    def get(self, request, *args, **kwargs):
        cur_date = datetime.datetime.now().date()
        cur_hour = datetime.datetime.now().hour + 1
        # 今天合计数据
        total_results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=cur_date)\
            .aggregate(total_money=Sum("cash_fee"))
        # 今天分时数据
        today_results = self.get_hour_money_data(cur_date, cur_hour)
        # 昨天分时数据
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        yesterday = yesterday.date()
        yesterday_results = self.get_hour_money_data(yesterday)
        data = {
            "total_money": total_results.get("total_money", 0),
            "today_money": today_results,
            "yesterday_money": yesterday_results,
        }
        return Response(data)

    def get_hour_money_data(self, current_date, limit_hour=24):
        """分时统计数据"""
        results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=current_date)\
            .extra(select={'hour': "HOUR(begin_time)"})\
            .values("hour").annotate(money=Sum("cash_fee")).order_by("hour")
        dict_results = {k: 0 for k in range(limit_hour)}
        for item in results:
            key = item["hour"]
            dict_results[key] = item["money"]
        return dict_results


# class TodayChargingMoney(APIView):
#     """今日充电电力"""
#     def get(self, request, *args, **kwargs):
#         pass