import datetime

from django.db.models import Sum, Count, F, Case, When, IntegerField
from rest_framework.response import Response
from rest_framework.views import APIView
from chargingorder.models import Order, OrderChargDetail
from django.db import connection

# 累计充电次数
# 累计充电电量
# 实时充电总功率
# 充电桩总数
from stationmanager.models import ChargingPile
from statistic.tasks import charging_yesterday_data, charging_device_stats, charging_accumulative_total_stats


class BigScreenChargStatsAPIView(APIView):
    """累计充电次数、累计充电电量、充电桩总数"""
    def get(self, request, *args, **kwargs):
        results = Order.objects.filter(status=2, consum_money__gt=0).\
            aggregate(accum_readings=Sum("total_readings"), accum_counts=Count("id"), accum_fees=Sum("consum_money"))

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
        total_results = Order.objects.filter(status=2, begin_time__date=cur_date).count()
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
        results = Order.objects.filter(status=2, begin_time__date=current_date)\
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
        total_results = Order.objects.filter(status=2, begin_time__date=cur_date)\
            .aggregate(total_readings=Sum("total_readings"))

        total_readings = total_results.get("total_readings", 0)
        if total_readings is None:
            total_readings = 0
        # 今天分时数据
        today_results = self.get_hour_readings_data(cur_date, cur_hour)
        # 昨天分时数据
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        yesterday = yesterday.date()
        yesterday_results = self.get_hour_readings_data(yesterday)
        data = {
            "total_readings": total_readings,
            "today_readings": list(today_results.values()),
            "yesterday_readings": list(yesterday_results.values()),
            "hour_list": list(yesterday_results.keys()),
        }
        return Response(data)

    def get_hour_readings_data(self, current_date, limit_hour=24):
        """分时统计数据"""
        results = Order.objects.filter(status=2, begin_time__date=current_date)\
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
        total_results = Order.objects.filter(status=2, begin_time__date=cur_date)\
            .aggregate(total_money=Sum("consum_money"))
        total_money = total_results.get("total_money", 0)
        if total_money is None:
            total_money = 0
        # 今天分时数据
        today_results = self.get_hour_money_data(cur_date, cur_hour)
        # 昨天分时数据
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        yesterday = yesterday.date()
        yesterday_results = self.get_hour_money_data(yesterday)
        data = {
            "total_money": total_money,
            "today_money": list(today_results.values()),
            "yesterday_money": list(yesterday_results.values()),
            "hour_list": list(yesterday_results.keys()),
        }
        return Response(data)

    def get_hour_money_data(self, current_date, limit_hour=24):
        """分时统计数据"""
        results = Order.objects.filter(status=2, begin_time__date=current_date)\
            .extra(select={'hour': "HOUR(begin_time)"})\
            .values("hour").annotate(money=Sum("consum_money")).order_by("hour")
        dict_results = {k: 0 for k in range(limit_hour)}
        for item in results:
            key = item["hour"]
            dict_results[key] = item["money"]
        return dict_results


class TodayChargingPowerAPIView(APIView):
    """今日充电电力"""
    def get(self, request, *args, **kwargs):
        cur_date = datetime.datetime.now().date()
        cur_hour = datetime.datetime.now().hour + 1
        # 今天合计数据
        total_results = OrderChargDetail.objects.filter(current_time__date=cur_date)\
            .aggregate(total_power=Sum(F("output_voltage") * F("output_current"))/1000)
        total_power = total_results.get("total_power", 0)
        if total_power is None:
            total_power = 0
        # 今天分时数据
        today_results = self.get_hour_power_data(cur_date, cur_hour)
        # 昨天分时数据
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        yesterday = yesterday.date()
        yesterday_results = self.get_hour_power_data(yesterday)
        data = {
            "total_power": total_power,
            "today_power": list(today_results.values()),
            "yesterday_power": list(yesterday_results.values()),
            "hour_list": list(yesterday_results.keys()),
        }
        return Response(data)

    def get_hour_power_data(self, current_date, limit_hour=24):
        """分时统计数据"""
        results = OrderChargDetail.objects.filter(current_time__date=current_date) \
            .extra(select={'hour': "HOUR(current_time)"}) \
            .values("hour").annotate(power=Sum(F("output_voltage") * F("output_current"))/1000).order_by("hour")
        dict_results = {k: 0 for k in range(limit_hour)}
        for item in results:
            key = item["hour"]
            dict_results[key] = item["power"]
        return dict_results


class CurrentMonthYearAccumAPIView(APIView):
    """当前月、年金额统计"""
    def get(self, request, *args, **kwargs):
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year
        # 月累计
        month_results = Order.objects.select_related("charg_pile").filter(status=2, begin_time__month=current_month)\
            .values(station_id=F("charg_pile__station"), station_name=F("charg_pile__station__name"))\
            .annotate(month_money=Sum("consum_money")).order_by("station_id")
        # 年累计
        year_results = Order.objects.select_related("charg_pile").filter(status=2, begin_time__year=current_year) \
            .values(station_id=F("charg_pile__station"), station_name=F("charg_pile__station__name")) \
            .annotate(year_money=Sum("consum_money")).order_by("station_id")
        result_dict = {}
        for result in month_results:
            result_dict[result["station_id"]] = result

        for res in year_results:
            station_id = res["station_id"]
            result_dict[station_id]["year_money"] = res["year_money"]

        return Response(result_dict.values())

