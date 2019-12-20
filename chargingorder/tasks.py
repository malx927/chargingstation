#-*-coding:utf-8-*-
from __future__ import absolute_import, unicode_literals

import decimal
import json
import random
import logging
import datetime
from time import sleep
from celery import shared_task
from celery.utils.log import get_task_logger
from channels.layers import get_channel_layer
from chargingorder.models import Order, ChargingStatusRecord, ChargingCmdRecord
from chargingorder.mqtt import server_publish, server_send_stop_charging_cmd
from chargingorder.utils import send_data_to_client, user_account_deduct_money
from chargingstation import settings
from codingmanager.models import FaultCode

from stationmanager.models import ChargingGun
from stationmanager.utils import connect_redis

logging.basicConfig(level=logging.INFO, filename='./logs/celery.log',
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s', filemode='a')

log = get_task_logger(__name__)


@shared_task
def update_pile_status_overtime():
    """
    超时处理
    电桩状态上报超时,设置电桩状态为离线
    """
    log.info('Enter update_pile_status_overtime task')
    for gun in ChargingGun.objects.exclude(work_status=9):
        update_time = gun.add_time
        current_time = datetime.datetime.now()
        if current_time < update_time:
            continue
        delta_time = (current_time - update_time).seconds
        print("---------------:", delta_time)
        if gun.charg_pile.pile_type not in [5, 6] and delta_time > settings.PILE_STATUS_OVER_TIME:     # 600
            # 更新pile状态 为离线状态
            log.info('update_pile_status_overtime:直流电桩SN{}枪口{}{}'.format(gun.charg_pile.pile_sn, gun.gun_num, '离线'))
            gun.work_status = 9
            gun.charg_status = None
            gun.add_time = datetime.datetime.now()
            gun.save(update_fields={"work_status", "charg_status", "add_time"})
        elif gun.charg_pile.pile_type in [5, 6] and delta_time > settings.PILE_AC_STATUS_OVER_TIME:     # 60 * 30
            # 更新pile状态 为离线状态
            log.info('update_pile_status_overtime:交流电桩SN{}枪口{}{}'.format(gun.charg_pile.pile_sn, gun.gun_num, '离线'))
            gun.work_status = 9
            gun.charg_status = None
            gun.add_time = datetime.datetime.now()
            gun.save(update_fields={"work_status", "charg_status", "add_time"})
    log.info('Leave update_pile_status_overtime task')

@shared_task
def send_start_stop_cmd_overtime():
    print('Enter send_charging_cmd_overtime')
    for rec in ChargingCmdRecord.objects.all():
        over_time = rec.over_time
        current_time = datetime.datetime.now()
        if current_time < over_time:
            continue
        print("send_charging_cmd_overtime:{}".format((current_time - rec.over_time).seconds))
        if (datetime.datetime.now() - rec.over_time).seconds > 20 or rec.send_count >= 3:
            try:
                order = Order.objects.get(out_trade_no=rec.out_trade_no)
                print("send_charging_cmd_overtime:订单{}".format(order.out_trade_no))
                if order.status == 2:
                    rec.delete()
                    continue

                fault_code = FaultCode.objects.get(id=92)  # 后台主动停止－通讯超时
                order.charg_status = fault_code
                order.status = 2
                order.save(update_fields={"status", "charg_status"})
                send_data = {
                    "return_code": "success",
                    "cmd": "07",  # 充电状态上报
                    "total_minutes": str(order.total_minutes()),
                    "total_reading": str(order.get_total_reading()),
                    "consum_money": str(order.consum_money.quantize(decimal.Decimal("0.01"))),
                    "charg_status": order.charg_status.name,
                    "order_status": order.get_status_display(),
                }
                print("send_charging_cmd_overtime:订单{}".format(order.out_trade_no))
                user_account_deduct_money(order)
            except Order.DoesNotExist as ex:
                log.warning(ex)
                send_data = {"return_code": "fail", "cmd": "07", "message": "订单不存在"}
            except FaultCode.DoesNotExist as ex:
                send_data = {"return_code": "fail", "cmd": "07", "message": "状态码不存在"}
                log.warning(ex)
            print("send_charging_cmd_overtime:订单{}".format(send_data))
            send_data_to_client(rec.pile_sn, rec.gun_num, **send_data)
            rec.delete()
            continue

        if datetime.datetime.now() >= rec.over_time and (datetime.datetime.now() - rec.over_time).seconds <= 20 and rec.send_count < 3:
            b_reply_proto = rec.send_cmd.encode("utf-8")
            print("{}--------{}.{}".format(rec.send_count, rec.send_cmd, rec.cmd_flag))
            server_publish(rec.pile_sn, b_reply_proto)
            rec.send_count = rec.send_count + 1
            rec.send_time = datetime.datetime.now()
            rec.over_time = datetime.datetime.now() + datetime.timedelta(seconds=settings.CHARGING_SEND_CMD_INTERVAL)
            rec.save()
    print('Leave send_charging_cmd_overtime')


@shared_task
def charging_status_overtime():
    """
    充电状态上报超时处理
    """
    log.info('Enter charging_status_overtime task')
    for record in ChargingStatusRecord.objects.all():
        over_time = record.over_time
        if datetime.datetime.now() > over_time:  # 15s 充电状态超时
            log.info('charging_status_overtime 超时:电桩SN:{} 枪口:{}订单:{}'.format(record.pile_sn, record.gun_num, record.out_trade_no))
            try:
                fault_code = FaultCode.objects.get(id=71)
                ChargingGun.objects.filter(charg_pile__pile_sn=record.pile_sn, gun_num=record.gun_num) \
                    .update(work_status=2, charg_status=fault_code)  # 2故障状态 71充电阶段超时
                order = Order.objects.get(out_trade_no=record.out_trade_no)
                if order.status == 2:
                    record.delete()
                    continue

                stop_cmd = {
                    "pile_sn": order.charg_pile.pile_sn,
                    "gun_num": int(order.gun_num),
                    "openid": order.openid,
                    "out_trade_no": order.out_trade_no,
                    "consum_money": int(order.consum_money.quantize(decimal.Decimal("0.01")) * 100),
                    "total_reading": int(order.get_total_reading() / decimal.Decimal(settings.FACTOR_READINGS)),
                    "stop_code": 0,  # 0 为后台主动停止
                    "fault_code": 71,  # 后台主动停止－通讯超时
                    "start_model": order.start_model,
                }
                server_send_stop_charging_cmd(**stop_cmd)  # 发送停止命令

            except Order.DoesNotExist as ex:
                log.warning(ex)
            except FaultCode.DoesNotExist as ex:
                log.warning(ex)
            # 删除状态命令
            record.delete()
    log.info('Leave update_pile_status_overtime task')


