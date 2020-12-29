#-*-coding:utf-8-*-
import datetime

from codingmanager.constants import GUN_WORKING_STATUS
from django.db.models import Sum, Count, F, DecimalField, Avg

from rest_framework.response import Response

from rest_framework.views import APIView

from chargingorder.models import Order, OrderChargDetail
from stationmanager.models import ChargingGun

__author__ = 'malixin'


class OrderTodayStatusStats(APIView):
    """订单状态分类统计"""
    def get(self, request, *args, **kwargs):

        if self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        cur_time = datetime.datetime.now().date()
        queryset = queryset.filter(begin_time__date=cur_time)
        # 已支付
        paid_count = queryset.filter(status=2).exclude(charg_status_id=6).count()
        # 待支付
        nopaid_count = queryset.filter(status=1).exclude(charg_status_id=6).count()
        # 充电中
        charg_count = queryset.filter(charg_status_id=6).count()
        # 故障数量
        faults = queryset.filter(charg_status__fault=1).count()
        # print(paid_count, nopaid_count, charg_count, faults)
        # 今日充电量
        total_readings = queryset.aggregate(readings=Sum("total_readings"))
        # 今日创建订单
        today_moneys = queryset.aggregate(total_moneys=Sum("consum_money"), power_fees=Sum("power_fee"), service_fees=Sum("service_fee"))
        # 昨日创建订单
        yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
        yesterday = yesterday.date()

        if self.request.user.station:
            orders = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            orders = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)
        else:
            orders = Order.objects.all()

        yesterday_moneys = orders.filter(begin_time__date=yesterday, end_time__date=cur_time).aggregate(total_moneys=Sum("consum_money"), power_fees=Sum("power_fee"), service_fees=Sum("service_fee"))

        paid = {"name": "已支付", "value": paid_count}
        nopaid = {"name": "未支付", "value": nopaid_count}
        charging = {"name": "充电中", "value": charg_count}

        total_moneys = today_moneys.get("total_moneys", 0) if today_moneys.get("total_moneys", 0) else 0
        yes_total_moneys = yesterday_moneys.get("total_moneys", 0) if yesterday_moneys.get("total_moneys", 0) else 0

        today_total_money = {"name": "今日创建订单", "value": total_moneys}
        yesterday_total_money = {"name": "昨日创建订单", "value": yes_total_moneys}

        results = dict()

        counts_dict = dict()
        counts_list = list()
        counts_list.append(charging)
        counts_list.append(nopaid)
        counts_list.append(paid)
        counts_dict["faults"] = faults
        counts_dict["counts"] = counts_list
        results["order_counts"] = counts_dict
        # 充电量
        readings = total_readings.get("readings", 0) if total_readings.get("readings", 0) else 0
        results["readings"] = readings
        # 金额
        money_dict = dict()
        money_list = list()
        money_list.append(today_total_money)
        money_list.append(yesterday_total_money)
        money_dict["moneys"] = money_list
        money_dict["total_moneys"] = total_moneys + yes_total_moneys

        today_power_fees = today_moneys.get("power_fees", 0) if today_moneys.get("power_fees", 0) else 0
        yes_power_fees = yesterday_moneys.get("power_fees", 0) if yesterday_moneys.get("power_fees", 0) else 0
        today_service_fees = today_moneys.get("service_fees", 0) if today_moneys.get("service_fees", 0) else 0
        yes_service_fees = yesterday_moneys.get("service_fees", 0) if yesterday_moneys.get("service_fees", 0) else 0

        money_dict["total_power_fees"] = today_power_fees + yes_power_fees
        money_dict["total_service_fees"] = today_service_fees + yes_service_fees
        results["order_moneys"] = money_dict

        # 充电枪状态
        if self.request.user.station:
            guns = ChargingGun.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            guns = ChargingGun.objects.filter(charg_pile__station__seller=self.request.user.seller)
        else:
            guns = ChargingGun.objects.all()

        gun_totals = guns.values("work_status").annotate(value=Count("id"))

        gun_status_list = [
            {"work_status": 0, "name": "空闲", "value": 0},
            {"work_status": 1, "name": "充电中", "value": 0},
            {"work_status": 2, "name": "故障", "value": 0},
            {"work_status": 3, "name": "占用未充电", "value": 0},
            {"work_status": 9, "name": "离线", "value": 0},
        ]

        for item in gun_status_list:
            for status in gun_totals:
                if item["work_status"] == status["work_status"]:
                    item["value"] = status["value"]
        results["gun_counts"] = gun_status_list
        return Response(results)


class OrderDayStats(APIView):
    """订单日统计"""
    def get(self, request, *args, **kwargs):
        flag = request.GET.get("flag", None)
        results = {
            "readings": 0,
            "counts": 0,
            "total_fees": 0,
            "times": 0,
            "service_fee": 0,
        }

        if self.request.user.is_superuser:
            queryset = Order.objects.filter(charg_pile__isnull=False)
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        if flag is None:    # 当天
            cur_time = datetime.datetime.now().date()
            results = queryset.filter(begin_time__date=cur_time)\
                .aggregate(
                    readings=Sum("total_readings"),
                    counts=Count("id"),
                    total_fees=Sum("consum_money"),
                    service_fees=Sum("service_fee"),
                    times=Sum((F("end_time") - F("begin_time"))/(1000000 * 60 * 60), output_field=DecimalField(decimal_places=2))
                )
        elif flag == "1":   # 昨天
            yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
            yesterday = yesterday.date()
            results = queryset.filter(status=2, begin_time__date=yesterday) \
                .aggregate(
                    readings=Sum("total_readings"),
                    counts=Count("id"),
                    total_fees=Sum("consum_money"),
                    service_fees=Sum("service_fee"),
                    times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2))
                )
        elif flag == "2":   # 任意天
            sdate = request.GET.get("sdate", None)
            if sdate:
                search_date = datetime.datetime.strptime(sdate, "%Y-%m-%d")
                s_date = search_date.date()
                results = queryset.filter(status=2, begin_time__date=s_date) \
                    .aggregate(
                        readings=Sum("total_readings"),
                        counts=Count("id"),
                        total_fees=Sum("consum_money"),
                        service_fees=Sum("service_fee"),
                        times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2))
                    )
        results["readings"] = 0.00 if results["readings"] is None else results["readings"]
        results["total_fees"] = 0.00 if results["total_fees"] is None else results["total_fees"]
        results["times"] = 0.00 if results["times"] is None else results["times"]
        results["service_fees"] = 0.00 if results["service_fees"] is None else results["service_fees"]
        return Response(results)


class OrderMonthStats(APIView):
    """月统计"""
    def get(self, request, *args, **kwargs):
        month = request.GET.get("month", None)
        if self.request.user.is_superuser:
            queryset = Order.objects.filter(charg_pile__isnull=False)
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        if month is None:  # 当月
            cur_time = datetime.datetime.now()
            results = queryset.filter(begin_time__year=cur_time.year, begin_time__month=cur_time.month) \
                .aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2))
            )
        else:  # 任意月
            s_date = datetime.datetime.strptime(month, "%Y-%m")
            results = queryset.filter(begin_time__year=s_date.year, begin_time__month=s_date.month) \
                .aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2))
            )

        results["readings"] = 0.00 if results["readings"] is None else results["readings"]
        results["total_fees"] = 0.00 if results["total_fees"] is None else results["total_fees"]
        results["times"] = 0.00 if results["times"] is None else results["times"]
        results["service_fees"] = 0.00 if results["service_fees"] is None else results["service_fees"]
        return Response(results)


class OrderYearStats(APIView):
    """年统计"""
    def get(self, request, *args, **kwargs):
        year = request.GET.get("year", None)
        if self.request.user.is_superuser:
            queryset = Order.objects.filter(charg_pile__isnull=False)
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        if year is None:  # 当年
            cur_time = datetime.datetime.now()
            results = queryset.filter(status=2, begin_time__year=cur_time.year) \
                .aggregate(
                    readings=Sum("total_readings"),
                    counts=Count("id"),
                    total_fees=Sum("consum_money"),
                    service_fees=Sum("service_fee"),
                    times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2))
                )
        else:  # 任意年

            results = queryset.filter(status=2, begin_time__year=int(year)) \
                .aggregate(
                    readings=Sum("total_readings"),
                    counts=Count("id"),
                    total_fees=Sum("consum_money"),
                    service_fees=Sum("service_fee"),
                    times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2))
                )

        results["readings"] = 0.00 if results["readings"] is None else results["readings"]
        results["total_fees"] = 0.00 if results["total_fees"] is None else results["total_fees"]
        results["times"] = 0.00 if results["times"] is None else results["times"]
        results["service_fees"] = 0.00 if results["service_fees"] is None else results["service_fees"]
        return Response(results)


class OrderCategoryStats(APIView):
    """分类统计"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        begin_time = request.GET.get("begin_time", None)
        end_time = request.GET.get("end_time", None)
        print("category=", category)
        if category is None or category == "":
            category = "1"

        if self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        if begin_time and end_time:
            b_date = datetime.datetime.strptime(begin_time, "%Y-%m-%d")
            e_date = datetime.datetime.strptime(end_time, "%Y-%m-%d")
            queryset = queryset.filter(status=2, begin_time__date__range=[b_date, e_date])
        else:
            queryset = queryset.filter(status=2)

        result = None
        if category == "1":     # 按运营商统计
            result = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name").order_by("charg_pile__station__seller").\
                annotate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
        elif category == "2":     # 按充电站统计
            result = queryset.values("charg_pile__station__seller__name", "charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station"). \
                            annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
        elif category == "3":     # 按充电桩统计
            result = queryset.values("charg_pile", "charg_pile__name", "charg_pile__station__seller__name", "charg_pile__station__name")\
                            .order_by("charg_pile"). \
                            annotate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )

        return Response(result)


class OrderDayAnalysis(APIView):
    """日统计分析"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        s_date = request.GET.get("s_date", None)

        if category is None or category == "":
            category = "1"

        if self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        if s_date:
            d_date = datetime.datetime.strptime(s_date, "%Y-%m-%d")
            queryset = queryset.filter(status=2, begin_time__date=d_date)
        else:
            queryset = queryset.filter(status=2, )

        totals = None
        if category == "1":     # 按运营商统计
            results = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name")\
                            .order_by("charg_pile__station__seller")\
                            .annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results
        elif category == "2":     # 按充电站统计
            results = queryset.values("charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station")\
                            .annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results
        elif category == "3":     # 按充电桩统计
            results = queryset.values("charg_pile", "charg_pile__name")\
                            .order_by("charg_pile")\
                            .annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results

        return Response(totals)


class OrderMonthAnalysis(APIView):
    """月统计分析"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        s_month = request.GET.get("s_month", None)

        if category is None or category == "":
            category = "1"

        if self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        if s_month:
            d_date = datetime.datetime.strptime(s_month, "%Y-%m")
            queryset = queryset.filter(status=2, begin_time__year=d_date.year, begin_time__month=d_date.month)
        else:
            queryset = queryset.filter(status=2)

        totals = None
        if category == "1":     # 按运营商统计
            results = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name")\
                            .order_by("charg_pile__station__seller")\
                            .annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results
        elif category == "2":     # 按充电站统计
            results = queryset.values("charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station")\
                            .annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results
        elif category == "3":     # 按充电桩统计
            results = queryset.values("charg_pile", "charg_pile__name")\
                            .order_by("charg_pile")\
                            .annotate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results

        return Response(totals)


class OrderYearAnalysis(APIView):
    """年统计分析"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        s_year = request.GET.get("s_year", None)

        if category is None or category == "":
            category = "1"

        if self.request.user.station:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__isnull=False, charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.filter(charg_pile__isnull=False)

        if s_year:
            d_date = datetime.datetime.strptime(s_year, "%Y")
            queryset = queryset.filter(status=2, begin_time__year=d_date.year)
        else:
            queryset = queryset.filter(status=2)

        totals = None
        if category == "1":     # 按运营商统计
            results = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name")\
                            .order_by("charg_pile__station__seller")\
                            .annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results
        elif category == "2":     # 按充电站统计
            results = queryset.values("charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station")\
                            .annotate(
                                readings=Sum("total_readings"),
                                counts=Count("id"),
                                total_fees=Sum("consum_money"),
                                service_fees=Sum("service_fee"),
                                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
                            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results
        elif category == "3":     # 按充电桩统计
            results = queryset.values("charg_pile", "charg_pile__name")\
                            .order_by("charg_pile")\
                            .annotate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals = queryset.aggregate(
                readings=Sum("total_readings"),
                counts=Count("id"),
                total_fees=Sum("consum_money"),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60))
            )
            totals["results"] = results

        return Response(totals)


class OrderDetailAPIView(APIView):
    """充电监控"""
    def get(self, request, *args, **kwargs):
        out_trade_no = kwargs.get("out_trade_no", None)
        order = Order.objects.filter(out_trade_no=out_trade_no).first()

        totals = {}
        results = OrderChargDetail.objects.filter(out_trade_no=out_trade_no)\
            .extra(select={'curr_time': "DATE_FORMAT(`current_time`, '%%y-%%m-%%d %%H:%%i')"})\
            .values("curr_time")\
            .annotate(voltage=Avg("voltage"), current=Avg("current"), output_voltage=Avg("output_voltage"), output_current=Avg("output_current"))\
            .order_by("curr_time")

        totals["out_trade_no"] = out_trade_no
        totals["begin_time"] = order.begin_time.strftime("%Y-%m-%d %H:%M:%S")
        totals["end_time"] = order.end_time.strftime("%Y-%m-%d %H:%M:%S")
        totals["total_readings"] = order.total_readings
        totals["consum_money"] = order.consum_money
        totals["results"] = results

        return Response(totals)