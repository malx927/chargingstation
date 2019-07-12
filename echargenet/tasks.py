#-*-coding:utf-8-*-
from __future__ import absolute_import, unicode_literals

import json
import random
from datetime import datetime, timedelta
from time import sleep
from celery import shared_task
from chargingorder.models import Order
from chargingstation import settings
from django.db.models import Q, Max, Count, Sum, F, Min

from echargenet.models import ConnectorInfo, CheckChargeOrder, DisputeOrder
from echargenet.utils import data_encode, get_hmac_md5, EchargeNet, data_decode, get_order_status, \
    get_equipment_connector_status
from stationmanager.models import ChargingGun


@shared_task
def notification_start_charge_result(start_charge_seq, connector_id):
    """
    接口名称：notification_start_charge_result
    使用要求：充电桩实际启动成功或失败后，应立即将启动结果信息同步推送至市级平台e充网，时
    间应控制在启动命令下发后50秒内
    """
    Data = {
        "StartChargeSeq": start_charge_seq,
        "ConnectorID": connector_id,
    }
    # Ret = 0
    # Msg = ""
    try:
        sleep(5)
        order = Order.objects.get(start_charge_seq=start_charge_seq)
        if order.begin_time:
            Data["StartTime"] = order.begin_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            Data["StartTime"] = datetime.now().strptime("%Y-%m-%d %H:%M:%S")

        Data["StartChargeSeqStat"] = get_order_status(order.charg_status.id)

    except Order.DoesNotExist as ex:
        Data["StartChargeSeqStat"] = 5
        Data["StartTime"] = datetime.now().strptime("%Y-%m-%d %H:%M:%S")
        # Msg = "Order Not Exists"

    # encrypt_data = data_encode(**Data)  # 数据加密
    # # 数据签名, 用Ret+Msg+Data生成返回签名
    # sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
    # ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
    # result = {
    #     "Ret": Ret,
    #     "Msg": Msg,
    #     "Data": encrypt_data,
    #     "Sig": ret_sig,
    # }
    echarge = EchargeNet(settings.MQTT_REDIS_URL, settings.MQTT_REDIS_PORT)
    status = echarge.notification_start_charge_result(**Data)
    if status > 0:
        print("推送启动充电结果失败!", status)
    else:
        print("推送启动充电结果成功!", status)


# 定时任务
@shared_task
def notification_equip_charge_status():
    """
    推送充电状态
    使用要求：充电桩开始充电后，均须每间隔50秒向市级平台e充网推送一次充电状态数据
    :return:
    """
    orders = Order.objects.filter(Q(status=None) | Q(status=0) | Q(status=1), start_charge_seq__isnull=False)

    for order in orders:
        result = {}
        gun_num = order.gun_num
        ConnectorID = '{0}{1}'.format(order.charg_pile.pile_sn, gun_num)
        gun = ChargingGun.objects.get(charg_pile=order.charg_pile, gun_num=gun_num)
        result["ConnectorID"] = ConnectorID
        result["StartChargeSeq"] = order.start_charge_seq

        result["StartChargeSeqStat"] = get_order_status(order.charg_status.id)
        result["ConnectorStatus"] = get_equipment_connector_status(gun.work_status, order.charg_status.id)

        # A 相电流  A 相电压
        if order.begin_time is None or order.end_time is None:
            continue

        result["CurrentA"] = 0
        result["VoltageA"] = 0
        result["Soc"] = order.end_soc
        result["StartTime"] = order.begin_time.strftime("%Y-%m-%d %H:%M:%S")
        result["EndTime"] = order.end_time.strftime("%Y-%m-%d %H:%M:%S")
        result["TotalPower"] = order.get_total_reading()
        result["TotalMoney"] = order.consum_money

        echarge = EchargeNet(settings.MQTT_REDIS_URL, settings.MQTT_REDIS_PORT)
        status = echarge.notification_equip_charge_status(**result)
        if status > 0:
            print("推送充电状态失败!", status)
        else:
            print("推送充电状态成功!", status)


@shared_task
def notification_stop_charge_result(start_charge_seq, connector_id):
    """
    接口名称：notification_stop_charge_result
    当充电桩实际停止充电后须立即推送结果信息到市级平台e充网，从充电桩收到停止命
    令到向市级平台e充网推送充电停止结果时间间隔控制在50秒内
    :return:
    """
    Data = {
        "StartChargeSeq": start_charge_seq,
        "ConnectorID": connector_id,
    }
    # Ret = 0
    # Msg = ""
    try:
        sleep(5)
        order = Order.objects.get(start_charge_seq=start_charge_seq)

        Data["StartChargeSeqStat"] = get_order_status(order.charg_status.id)

    except Order.DoesNotExist as ex:
        Data["StartChargeSeqStat"] = 5
        # Msg = "Order Not Exists"

    # encrypt_data = data_encode(**Data)  # 数据加密
    # # 数据签名, 用Ret+Msg+Data生成返回签名
    # sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
    # ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
    # result = {
    #     "Ret": Ret,
    #     "Msg": Msg,
    #     "Data": encrypt_data,
    #     "Sig": ret_sig,
    # }
    echarge = EchargeNet(settings.MQTT_REDIS_URL, settings.MQTT_REDIS_PORT)
    status = echarge.notification_stop_charge_result(**Data)
    if status > 0:
        print("推送停止充电结果失败!", status)
    else:
        print("推送停止充电结果成功!", status)

    connector_status = echarge.notification_station_status(connector_id, 0)  # 设置为空闲状态
    if status > 0:
        print("设备状态变化推送失败!", connector_status)
    else:
        print("设备状态变化推送成功!", connector_status)


@shared_task
def notification_charge_order_info_for_bonus():
    """
    推送充电订单信息（运营考核奖励）
    使用要求：自充电桩停止充电并生成订单后，订单须在150秒内上报到市级平台e充网，如上报失败
    须按照以下频率推送订单信息(150/300/…./1800/3600/….，单位秒)
    """
    orders = Order.objects.filter(Q(report_result__isnull=True) | Q(report_result__gt=0), start_charge_seq__isnull=False, status=2)
    result ={}
    # Ret = 0
    # Msg = ""
    for order in orders:
        if order.begin_time is None or order.end_time is None:
            continue

        if order.report_time is not None:
            if (datetime.now() - order.report_time).seconds < 145:
                continue

        try:
            gun = ChargingGun.objects.get(charg_pile=order.charg_pile, gun_num=order.gun_num)
        except ChargingGun.DoesNotExist as ex:
            gun = None

        ConnectorID = '{}{}'.format(order.charg_pile.pile_sn, order.gun_num)
        result["StartChargeSeq"] = order.start_charge_seq
        result["ConnectorID"] = ConnectorID
        result["StartTime"] = order.begin_time.strftime("%Y-%m-%d %H:%M:%S")
        result["EndTime"] = order.end_time.strftime("%Y-%m-%d %H:%M:%S")
        result["ChargeModel"] = 0
        result["TotalPower"] = str(order.get_total_reading())
        result["TotalMoney"] = str(order.consum_money)
        result["UserName"] = order.name
        result["StationID"] = str(order.charg_pile.station.id)
        result["EquipmentID"] = order.charg_pile.pile_sn
        result["ConnectorPower"] = gun.power if gun is not None else 0
        result["ChargeLast"] = order.total_seconds()
        result["MeterValueStart"] = str(order.begin_reading)
        result["MeterValueEnd"] = str(order.end_reading)
        if order.charg_status.id == 91:
            result["StopReason"] = 0    # 用户手动停止充电
        elif order.charg_status.id in [95, 96]:
            result["StopReason"] = 3    # 充电机设备故障
        elif order.charg_status.id in [98, 92]:
            result["StopReason"] = 4    # 连接器断开
        elif order.charg_status.id in [93, 94, 97]:
            result["StopReason"] = 1    # 客户归属地运营商平台停止充

        # encrypt_data = data_encode(**result)  # 数据加密
        # # 数据签名, 用Ret+Msg+Data生成返回签名
        # sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
        # ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        # result = {
        #     "Ret": Ret,
        #     "Msg": Msg,
        #     "Data": encrypt_data,
        #     "Sig": ret_sig,
        # }
        echarge = EchargeNet(settings.MQTT_REDIS_URL, settings.MQTT_REDIS_PORT)
        ret_data = echarge.notification_charge_order_info_for_bonus(**result)

        if "Ret" in ret_data and ret_data["Ret"] == 0:
            # 解密
            ret_crypt_data = ret_data["Data"]
            ret_decrypt_data = data_decode(ret_crypt_data)
            # 获取到code值
            dict_decrpt_data = json.loads(ret_decrypt_data)
            print(dict_decrpt_data["StartChargeSeq"])
            ConfirmResult = dict_decrpt_data["ConfirmResult"]
        else:
            ConfirmResult = 99

        order.report_result = ConfirmResult
        order.report_time = datetime.now()
        order.save()
        if ConfirmResult > 0:
            print("推送充电订单信息失败!", ConfirmResult)
        else:
            print("推送充电订单信息成功!", ConfirmResult)


# 定时任务
@shared_task
def notification_connector_status():
    """定时推送设备接口状态"""
    connectors = ConnectorInfo.objects.all()
    echarge = EchargeNet(settings.MQTT_REDIS_URL, settings.MQTT_REDIS_PORT)
    for connector in connectors:
        status = echarge.notification_station_status(connector.ConnectorID, connector.Status)
        if status > 0:
            print("设备状态变化推送失败:{},{}".format(connector.ConnectorID, status))
        else:
            print("设备状态变化推送成功:{},{}".format(connector.ConnectorID, status))


# 定时任务
@shared_task
def check_charge_orders():
    """
    接口名称：check_charge_orders
    使用要求：每天0点到3点之间推送前一天市级平台e充网启动的所有订单信息
    1、是否是经过上报的订单
    2、开始时间还是结束时间(跨天问题)
    """
    prev_date = datetime.now().date() - timedelta(days=1)
    print("当前时间:", prev_date)
    order_totals = Order.objects.filter(end_time__date=prev_date, start_charge_seq__isnull=False, status=2, charg_pile__is_subsidy=1)\
        .aggregate(
            start_time=Min("end_time"), end_time=Max("end_time"), order_count=Count("out_trade_no"),
            total_power=Sum(F("end_reading") - F("begin_reading")), total_money=Sum("consum_money")
        )
    print(order_totals)
    check_orders = {}
    check_order_seq = '{0}{1}{2}'.format(settings.OPERATORID, datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
    check_orders["CheckOrderSeq"] = check_order_seq
    if order_totals["start_time"]:
        check_orders["StartTime"] = order_totals["start_time"].strftime("%Y-%m-%d %H:%M:%S")
    else:
        check_orders["StartTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if order_totals["end_time"]:
        check_orders["EndTime"] = order_totals["end_time"].strftime("%Y-%m-%d %H:%M:%S")
    else:
        check_orders["EndTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    check_orders["OrderCount"] = order_totals["order_count"]
    check_orders["TotalOrderPower"] = float(order_totals["total_power"])
    check_orders["TotalOrderMoney"] = float(order_totals["total_money"])

    orders = Order.objects.filter(end_time__date=prev_date, start_charge_seq__isnull=False,
                                  status=2, charg_pile__is_subsidy=1)
    charge_orders = []
    for order in orders:
        d_order = {}
        d_order["StartChargeSeq"] = order.start_charge_seq
        d_order["TotalPower"] = float(order.get_total_reading())
        d_order["TotalMoney"] = float(order.consum_money)
        charge_orders.append(d_order)

    check_orders["ChargeOrders"] = charge_orders
    print(json.dumps(check_orders))

    echarge = EchargeNet(settings.MQTT_REDIS_URL, settings.MQTT_REDIS_PORT)
    ret_data = echarge.check_charge_orders(**check_orders)
    if "Ret" in ret_data and ret_data["Ret"] == 0:
        # 解密
        ret_crypt_data = ret_data["Data"]
        ret_decrypt_data = data_decode(ret_crypt_data)
        # 获取到code值
        dict_decrpt_data = json.loads(ret_decrypt_data)
        check_order = {
            "CheckOrderSeq": dict_decrpt_data["CheckOrderSeq"],
            "StartTime": datetime.strptime(dict_decrpt_data["StartTime"], '%Y-%m-%d %H:%M:%S'),
            "EndTime": datetime.strptime(dict_decrpt_data["EndTime"], '%Y-%m-%d %H:%M:%S'),
            "TotalDisputeOrder": dict_decrpt_data["TotalDisputeOrder"],
            "TotalDisputePower": dict_decrpt_data["TotalDisputePower"],
            "TotalDisputeMoney": dict_decrpt_data["TotalDisputeMoney"],
        }
        CheckChargeOrder.objects.create(**check_order)
        DisputeOrders = dict_decrpt_data["DisputeOrders"]
        for disOrder in DisputeOrders:
            DisputeOrder.objects.create(**disOrder)
    else:
       print(ret_data["Msg"])


