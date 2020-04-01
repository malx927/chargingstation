#-*-coding:utf-8-*-
from __future__ import absolute_import, unicode_literals

import decimal
import json
import random
import logging
import datetime
import time
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import connection
from django.db.models import Count, Sum, F, Case, When, IntegerField, FloatField, Q

from django_redis import get_redis_connection

from chargingorder.models import Order, OrderChargDetail
from stationmanager.models import ChargingPile

log = get_task_logger(__name__)


def get_hour_data(current_date, limit_hour=24):
    """分时统计数据"""
    # 充电次数,充电量,充电金额
    charging_stats = Order.objects.filter(begin_time__date=current_date) \
        .extra(select={'hour': "HOUR(begin_time)"}) \
        .values("hour").annotate(count=Count("id"), readings=Sum("total_readings"), money=Sum("consum_money")).order_by("hour")

    power_stats = OrderChargDetail.objects.filter(current_time__date=current_date) \
        .extra(select={'hour': "HOUR(`current_time`)"}) \
        .values("hour").annotate(power=Sum(F("output_voltage") * F("output_current")) / 1000).order_by("hour")

    count_results = {k: 0 for k in range(limit_hour)}
    readings_results = {k: 0 for k in range(limit_hour)}
    money_results = {k: 0 for k in range(limit_hour)}
    for item in charging_stats:
        key = item["hour"]
        count_results[key] = item["count"]
        readings_results[key] = int(item["readings"])
        money_results[key] = int(item["money"])

    power_results = {k: 0 for k in range(limit_hour)}
    for item in power_stats:
        key = item["hour"]
        power_results[key] = int(item["power"])

    dict_results = dict()
    dict_results["count"] = count_results
    dict_results["readings"] = readings_results
    dict_results["money"] = money_results
    dict_results["power"] = power_results

    return dict_results


@shared_task
def charging_yesterday_data():
    """
    更新昨天数据到redis,充电次数、充电电量、充电金额、充电电力
    """
    log.info('Enter update_yesterday_data task')
    yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
    yesterday = yesterday.date()

    yesterday_results = get_hour_data(yesterday)
    conn = get_redis_connection("default")

    conn.hmset("yd_yesterday_hour_count", yesterday_results.get("count"))
    conn.hmset("yd_yesterday_hour_readings", yesterday_results.get("readings"))
    conn.hmset("yd_yesterday_hour_money", yesterday_results.get("money"))
    conn.hmset("yd_yesterday_hour_power", yesterday_results.get("power"))

    log.info('Leave update_yesterday_data task')


@shared_task
def charging_device_stats():
    """充电桩设备分组统计和合计"""
    log.info('Enter charging_device_stats')
    results = ChargingPile.objects.select_related("station").values("station", "station__name"). \
        order_by("station").annotate(
        dc_device=Sum(Case(When(pile_type__in=[1, 2], then=1), default=0, output_field=IntegerField())),
        ac_device=Sum(Case(When(pile_type__in=[5, 6], then=1), default=0, output_field=IntegerField())),
    )
    device_counts = ChargingPile.objects.count()
    conn = get_redis_connection("default")

    conn.set("yd_device_category_stats", json.dumps(list(results)))
    conn.set("yd_device_counts", device_counts)
    log.info('Leave charging_device_stats')


@shared_task
def charging_accumulative_total_stats():
    """
    充电累计数量统计：累计电量、累计次数、累计金额
    """
    log.info('Enter charging_accumulative_total_stats task')

    results = Order.objects.filter(status=2, consum_money__gt=0). \
        aggregate(accum_readings=Sum("total_readings"), accum_counts=Count("id"), accum_fees=Sum("consum_money"))

    conn = get_redis_connection("default")

    conn.set("yd_accum_readings", float(results.get("accum_readings", 0)))
    conn.set("yd_accum_counts", results.get("accum_counts", 0))
    conn.set("yd_accum_fees", float(results.get("accum_fees", 0)))

    log.info('Leave charging_accumulative_total_stats task')


@shared_task
def current_month_year_accumlative_stats():
    """当月和当年的累计统计数据"""
    log.info('Enter current_month_year_accumlative_stats task')
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    # 月累计
    month_results = Order.objects.select_related("charg_pile").filter(status=2, begin_time__year=current_year,
                                                                      begin_time__month=current_month) \
        .values(station_id=F("charg_pile__station"), station_name=F("charg_pile__station__name")) \
        .annotate(month_money=Sum("consum_money", output_field=FloatField())).order_by("station_id")
    print(month_results)
    # print(connection.queries)
    # 年累计
    year_results = Order.objects.select_related("charg_pile").filter(status=2, begin_time__year=current_year) \
        .values(station_id=F("charg_pile__station"), station_name=F("charg_pile__station__name")) \
        .annotate(year_money=Sum("consum_money", output_field=FloatField())).order_by("station_id")
    print(year_results)

    result_dict = {}
    for result in month_results:
        result_dict[result["station_id"]] = result

    for res in year_results:
        station_id = res["station_id"]
        result_dict[station_id]["year_money"] = res["year_money"]
    # print("current_month_year_accumlative_stats:", result_dict)
    results = result_dict.values()
    conn = get_redis_connection("default")
    conn.set("yd_current_mon_year_accum_stats", json.dumps(list(results)))
    log.info('Leave current_month_year_accumlative_stats task')


@shared_task
def real_time_power_stats():
    """实时电力统计"""
    search_date = datetime.datetime.now() + datetime.timedelta(days=-1)
    results = Order.objects.filter(charg_status_id=6, begin_time__date__gte=search_date.date()). \
        aggregate(realtime_power=Sum(F("output_voltage") * F("output_current"), output_field=FloatField()) / 1000)

    conn = get_redis_connection("default")
    realtime_power = results.get("realtime_power", 0) if results.get("realtime_power", 0) is not None else 0

    conn.set("yd_real_time_power_stats", realtime_power)


@shared_task
def charging_today_data():
    """当天充电次数、充电电量、充电金额、充电电力"""
    cur_date = datetime.datetime.now().date()
    # yester_date = (datetime.datetime.now() + datetime.timedelta(days=-1)).date()
    today_totals = Order.objects.filter(begin_time__date=cur_date)\
        .aggregate(today_total_counts=Count("id"), today_total_readings=Sum("total_readings", output_field=FloatField()), today_total_money=Sum("consum_money", output_field=FloatField()))
    log.info(today_totals)

    today_total_power = OrderChargDetail.objects.filter(current_time__date=cur_date) \
        .aggregate(today_total_power=Sum(F("output_voltage") * F("output_current")) / 1000)
    log.info(today_total_power)

    cur_date = datetime.datetime.now().date()
    cur_hour = datetime.datetime.now().hour + 1
    today_results = get_hour_data(cur_date, cur_hour)

    conn = get_redis_connection("default")

    today_total_counts = today_totals.get("today_total_counts") if today_totals.get("today_total_counts") is not None else 0
    today_total_readings = today_totals.get("today_total_readings") if today_totals.get("today_total_readings") is not None else 0
    today_total_money = today_totals.get("today_total_money") if today_totals.get("today_total_money") is not None else 0

    today_total_power = today_total_power.get("today_total_power") if today_total_power.get("today_total_power") is not None else 0

    conn.set("yd_today_total_counts", today_total_counts)
    conn.set("yd_today_total_readings", today_total_readings)
    conn.set("yd_today_total_money", today_total_money)
    conn.set("yd_today_total_power", today_total_power)

    conn.delete("yd_today_hour_count")
    conn.delete("yd_today_hour_readings")
    conn.delete("yd_today_hour_money")
    conn.delete("yd_today_hour_power")
    conn.hmset("yd_today_hour_count", today_results.get("count"))
    conn.hmset("yd_today_hour_readings", today_results.get("readings"))
    conn.hmset("yd_today_hour_money", today_results.get("money"))
    conn.hmset("yd_today_hour_power", today_results.get("power"))

