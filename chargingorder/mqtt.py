# coding=utf-8
import base64
import decimal
import json
import logging
import random

from chargingorder.models import Order, ChargingCmdRecord
from paho import mqtt
import paho.mqtt.publish as publish
from datetime import datetime
from chargingstation import settings

__author__ = 'Administrator'

# logging.basicConfig(level=logging.INFO, )
logging.basicConfig(level=logging.INFO, filename='./logs/charging_django.log',
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s', filemode='a')
from .utils import get_32_byte, get_byte_daytime, get_pile_sn, byte2integer, uchar_checksum, get_data_nums, \
    message_escape, save_charging_cmd_to_db
from codingmanager.constants import *

SUB_TOPIC = 'sub'
PUB_TOPIC = 'pub'


def server_publish(pile_sn, data):

    topic = '/{0}/{1}'.format(pile_sn, SUB_TOPIC)
    auth = {
        'username': settings.USERNAME,
        'password': settings.PASSWORD,
    }
    print(topic, auth)
    print("server_publish:", data.hex())
    publish.single(topic, payload=data, qos=0, retain=False, hostname=settings.MQTT_HOST, port=1883,
                   client_id=settings.DEVICENAME_SEND, keepalive=60, will=None, auth=auth)


# 7 (0x84)
def server_send_charging_cmd(*args, **kwargs):
    """
    服务器向充电桩下发充电指令 命令号0x84
    命令号0x84（1字节） + 枪口号（1字节）+ 充电类型（1字节）+ 充电策略（2字节）+ 充电策略值（4字节）+ 用户识别号（32字节）+ 订单号（32字节）
    + 同步时间（7字节） + 保留（8字节）
    此函数由用户扫描缴费调用，通过二维码的pile_sn 和 gun_nums确定后台的数据内容
    :return:
    """
    logging.info("Enter server_send_charging_cmd function")
    pile_sn = kwargs.get("pile_sn", None)
    b_pile_sn = get_32_byte(pile_sn)
    b_command = CMD_SEND_CHARGING
    # 枪口号
    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])
    # 充电类型（来至前台）
    charg_type = kwargs.get("charging_type", 0)
    subscribe_min = kwargs.get("subscribe_min", 0)
    b_charging_type = bytes([charg_type << 7 | subscribe_min & 0x7f])

    # 充电策略 1、充电模式(后台or本地离线)  根据前台用户信息判断 000充满为止，001按金额，010按分钟数，011按SOC 100按电量
    charging_category = kwargs.get("charging_category", 0)  # D15-D14
    charging_way = kwargs.get("charging_way", 0)  # D13－D11
    # 充电策略是否使用(D0：1使用充电策略，0系统默认策略)
    continue_charg_status = kwargs.get("continue_charg_status", 0)  # 断网可继续充电
    occupy_fee_status = kwargs.get("occupy_status", 0)  # 收取占位费
    subscribe_fee_status = kwargs.get("subscribe_status", 0)  # 收取预约费
    low_fee_status = kwargs.get("low_fee_status", 0)  # 收取小电流补偿费
    low_restrict_status = kwargs.get("low_restrict_status", 0)  # 限制小电流输出
    use_policy_flag = kwargs.get("use_policy_flag", 0)

    charging_policy1 = charging_category << 6 & 0xFF | charging_way << 3 & 0xFF | continue_charg_status << 2 & 0xFF \
                       | occupy_fee_status << 1 & 0xFf | subscribe_fee_status & 0xFF
    charging_policy2 = low_fee_status << 7 & 0xFF | low_restrict_status << 6 & 0xFF | use_policy_flag & 0xFf
    b_charging_policy1 = bytes([charging_policy1])
    b_charging_policy2 = bytes([charging_policy2])
    b_charging_policy = b''.join([b_charging_policy1, b_charging_policy2])
    # 充电策略值
    charging_policy_value = kwargs.get("charging_policy_value", 0)
    b_charging_policy_value = charging_policy_value.to_bytes(4, byteorder='big')

    out_trade_no = kwargs.get("out_trade_no", "")  # 订单号
    b_out_trade_no = get_32_byte(out_trade_no)

    b_send_time = get_byte_daytime(datetime.now())  # 同步时间

    b_blank = bytes(8)  # 保留8字节

    b_data = b''.join([b_command, b_gun_num, b_charging_type, b_charging_policy,
                       b_charging_policy_value, b_out_trade_no, b_send_time, b_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    print("2:", byte_data.hex())
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])

    server_publish(pile_sn, b_reply_proto)

    # 保存充电命令用于超时判断
    save_charging_cmd_to_db(pile_sn, gun_num, out_trade_no, bytes.hex(b_reply_proto), "start")

    logging.info("Leave server_send_charging_cmd function")


# 12 (0x86)
def server_send_stop_charging_cmd(*args, **kwargs):
    """12、服务器主动下发停止充电或停止充电确认"""
    print("Enter server_send_stop_charging_cmd function")

    pile_sn = kwargs.get("pile_sn")
    if pile_sn is None:
        print("pile_sn can not be empty")
        return
    b_pile_sn = get_32_byte(pile_sn)

    out_trade_no = kwargs.get("out_trade_no", None)
    if out_trade_no is None:
        print("Order Can not Be Empty")
        return
    # 订单号
    b_out_trade_no = get_32_byte(out_trade_no)
    # 命令
    b_command = CMD_SEND_STOP_CHARG
    # 枪口号
    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])
    # 消费金额
    consum_money = kwargs.get("consum_money", None)
    if consum_money is None:
        try:
            order = Order.objects.get(out_trade_no=out_trade_no)
        except Order.DoesNotExist as ex:
            pass
        consum_money = order.consum_money * 100 if order is not None else 0
    if consum_money > 0:
        b_consum_money = int(consum_money).to_bytes(4, byteorder="big")
    else:
        b_consum_money = bytes([0])
    print("金额：", consum_money, b_consum_money.hex())
    # 总的电表数
    total_reading = kwargs.get("total_reading", 0)
    if total_reading < 0:
        total_reading = 0
    b_total_reading = total_reading.to_bytes(4, byteorder="big")
    print("电表数：", total_reading, b_total_reading.hex())
    # 停止标记
    stop_code = kwargs.get("stop_code", 0)
    b_stop_code = bytes([stop_code])
    print("停止标记：", stop_code, b_stop_code.hex())
    # 运行状态标记
    state_code = kwargs.get("state_code", 3)
    b_state_code = bytes([state_code])
    # 故障代码
    fault_code = kwargs.get("fault_code", 0)
    b_fault_code = bytes([fault_code])
    print("故障代码：", fault_code, b_fault_code.hex())
    # 保留
    b_blank = bytes(3)

    b_data = b''.join([b_command, b_gun_num, b_out_trade_no, b_consum_money, b_total_reading, b_stop_code, b_state_code, b_fault_code, b_blank])
    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    b_rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, b_rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, b_rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    server_publish(pile_sn, b_reply_proto)   # 发送主题
    # 保存充电命令
    save_charging_cmd_to_db(pile_sn, gun_num, out_trade_no, bytes.hex(b_reply_proto), "stop")
    print("Leave server_send_stop_charging_cmd function")