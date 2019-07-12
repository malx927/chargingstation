# coding=utf-8
import base64
import hashlib
import hmac

import os
import random
import sys
import json
import threading
import time
import signal
from datetime import datetime
import logging
import binascii
import math
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)

# # 导入django model
# BASEDIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.insert(0, BASEDIR)
# os.environ['DJANGO_SETTINGS_MODULE'] = 'chargingstation.settings'
# import django
# django.setup()
#
# from StationManager.utils import get_mqtt_param


# 电桩命令号
CMD_PILE_STATUS = b'\x01'
CMD_PILE_PARAMS = b'\x03'
CMD_PILE_CHARG_REPLY = b'\x04'
CMD_PILE_CAR_INFO = b'\x05'
CMD_PILE_CHARGING_STATUS = b'\x06'
CMD_PILE_STOP_CHARGING = b'\x07'
PILE_UPGRADE_FILESIZE = b'\x08'
PILE_UPGRADE_FILEDATA = b'\x09'
CMD_PILE_LOG_DATA = b'\x0a'
CMD_PILE_VERSION_INFO = b'\x81'
CMD_REQUEST_PILE_PARARMS = b'\x82'
CMD_SET_PILE_PARARMS = b'\x83'
CMD_SEND_CHARGING = b'\x84'
CMD_REPLY_CARINFO = b'\x85'
CMD_SEND_STOP_CHARG = b'\x86'
CMD_FORCE_STOP_CHARG = b'\x87'
CMD_REPLY_FILE_SIZE = b'\x88'
CMD_REPLY_FILE_DATA = b'\x89'
CMD_REQUEST_LOG_DATA = b'\x8a'
# 协议头尾字符
PROTOCAL_HEAD = b'\xAA\xAA'
PROTOCAL_TAIL = b'\x55\x55'

PRODUCTKEY = ''
DEVICENAME = 'abc12345'

# MQTT_URL = 'iot.hld8000.com'
MQTT_URL = 'www.canage.com.cn'
USERNAME = 'mqtt'
PASSWORD = 'abc123'

g_out_trade_no = None
g_pile_sn = None
g_gun_num = 0
g_openid = ""


def save_subscribe_msg(msg):
    """
    保存订阅消息
    :param msg:
    :return:
    """
    msg_data = {
        'topic': msg.topic,
        'recv_time': datetime.now(),
        'qos': msg.qos,
        'message': msg.payload,
        'retain': msg.retain
    }


def on_log(client, userdata, level, buf):
    logging.info(buf)


def on_disconnect(client, userdata, flags, rc=0):
    logging.info("client disconnected ok")
    client.connected_flag = False
    client.bad_connection_flag =True


# 连接成功回调函数
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True
        logging.info("connected ok")
        # 订阅设备状态：QOS=0
        topic = '/{0}/sub'.format(DEVICENAME)
        r = client.subscribe(topic, 0)
        if r[0] == 0:
            logging.info("subscribed to topic "+str(topic)+" return code" + str(r))
            client.topic_ack.append([topic, r[1], 0])
        else:
            logging.info("error on subscribing " + str(r) + ":" + topic)
    else:
        logging.info("Bad connection Returned code="+str(rc))
        client.bad_connection_flag = True


# 收到订阅消息回调函数
def on_message(client, userdata, msg):

    if len(msg.payload) <= 40:
        print(u'数据格式不合法')
        return
    ret_data = is_legal_message(msg.payload)
    if ret_data is None:
        print('判断数据协议不合法.......')
    # 报文解密
    decrypt_data = decrypt_message(ret_data)
    # 报文调度
    message_dispatch(msg.topic, decrypt_data)

    # print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))


def on_subscribe(client, userdata, mid, granted_qos):
    # 判断订阅成功和失败
    logging.debug("on subscribe callback result " + str(mid))
    if len(client.topic_ack) == 0:
        return

    for index, t in enumerate(client.topic_ack):
        if t[1] == mid:
            client.topic_ack.pop(index)

    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def message_dispatch(topic, byte_msg):
    """
    分发报文
    :param topic:
    :param byte_msg:
    :return:
    """
    byte_command = byte_msg[37:38]
    if byte_command == CMD_SEND_CHARGING:     # 接收到服务器充电命令

        client_reply_charging_cmd(topic, byte_msg)

    elif byte_command == CMD_PILE_VERSION_INFO:   # 接收服务器返回的版本信息

        client_version_info_handler(topic, byte_msg)

    elif byte_command == CMD_SEND_STOP_CHARG:   # 接收服务器发来的停止充电指令

        client_stop_charging_handler(topic, byte_msg)

    elif byte_command == CMD_FORCE_STOP_CHARG:   # 接收服务器的强制停充指令

        client_force_stop_charging_handler(topic, byte_msg)

    elif byte_command == CMD_SET_PILE_PARARMS:   # 接收服务器的配置电桩参数指令

        client_configure_pile_params(topic, byte_msg)

    elif byte_command == CMD_REQUEST_PILE_PARARMS:   # 接收到服务端的参数查询指令

        client_request_pile_params_handler(topic, byte_msg)

    # elif byte_command == PILE_UPGRADE_FILESIZE:   # 充电桩获取升级文件大小
    #
    #     pile_get_upgrade_filesize(topic, byte_msg)
    #
    # elif byte_command == PILE_UPGRADE_FILEDATA:   # 充电桩获取升级文件数据
    #
    #     pile_get_upgrade_filedata(topic, byte_msg)
    #
    # elif byte_command == CMD_PILE_LOG_DATA:   # 充电桩上报LOG数据
    #
    #     pile_log_data_report(topic, byte_msg)


# 0x05
def pile_report_car_info(*arg, **kwargs):
    """
    说明：充电桩->服务器，充电桩上报车辆信息，该信息在上报充电指令之后上报（128字节）。
    :param arg:
    :param kwargs: product_key, device_name, pile_sn,gun_num, openid,out_trade_no,charg_time, voltage,
                    current,output_voltage, output_current, current_readings
    :return:
    """
    print('Enter pile_report_car_info', kwargs)
    pile_sn = kwargs.get("pile_sn", None)

    if pile_sn is None:
        return
    # 桩SN
    b_pile_sn = get_32_byte(pile_sn)
    # 命令
    b_command = CMD_PILE_CAR_INFO
    # 枪口
    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])
    # 用户识别号
    openid = kwargs.get("openid", "")
    b_openid = get_32_byte(openid)
    # 订单号
    out_trade_no = kwargs.get("out_trade_no", "")
    b_out_trade_no = get_32_byte(out_trade_no)
    # 当前充电时间
    protocol = kwargs.get("protocol", 0)
    b_protocol = bytes([protocol])
    # 车辆VIN码
    vin_code = kwargs.get("vin_code", "")
    b_vin_code = get_32_byte(vin_code, 17)
    # 车辆最大单体电池电压
    max_single_voltage = kwargs.get("max_single_voltage", 0)
    b_max_single_voltage = max_single_voltage.to_bytes(2, byteorder="big")
    # 车辆最高充电电流
    max_current = kwargs.get("max_current", 0)
    b_max_current = max_current.to_bytes(2, byteorder="big")
    # 动力蓄电池标称总容量
    total_capacity = kwargs.get("total_capacity", 0)
    b_total_capacity = total_capacity.to_bytes(2, byteorder="big")
    # 车辆最高充电电压
    max_voltage = kwargs.get("max_voltage", 0)
    b_max_voltage = max_voltage.to_bytes(2, byteorder="big")
    # 车辆最高充电温度
    max_temp = kwargs.get("max_temp", 0)
    b_max_temp = max_temp.to_bytes(2, byteorder="big")
    # 初始SOC
    begin_soc = kwargs.get("begin_soc", 0)
    b_begin_soc = begin_soc.to_bytes(2, byteorder="big")
    # 初始电表数
    begin_reading = kwargs.get("begin_reading", 0)
    b_begin_reading = begin_reading.to_bytes(4, byteorder="big")

    b_blank = bytes(28)  # 保留28字节

    data = b''.join([b_command, b_gun_num, b_openid, b_out_trade_no, b_protocol, b_vin_code, b_max_single_voltage,
                     b_max_current, b_total_capacity, b_max_voltage, b_max_temp, b_begin_soc, b_begin_reading, b_blank])

    data_len = (len(data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, data])
    checksum = bytes([uchar_checksum(byte_proto_data)])

    b_reply_proto = b"".join([byte_proto_data, checksum, PROTOCAL_TAIL])
    # print(reply_proto)

    client_publish(pile_sn, b_reply_proto)
    # global b_car_info
    # b_car_info = False
    print('Leave pile_report_car_info')


def pile_charging_status_report(*arg, **kwargs):
    """
    11、充电状态上报
    说明：充电桩->服务器，上报充电过程数据，每10S左右更新一次，此命令无须服务器端回复（96字节）
    数据区：命令号0x06（1字节）+ 枪口号（1字节）+ 用户识别号（32字节）+订单号（32字节）+时间（7字节）+所需电压值（2字节）+所需电流值（2字节）+输出电压值（2字节）
        +输出电流值（2字节）+当前电表读数（4字节）+保留（11字节）
    :param arg:
    :param kwargs: product_key, device_name, pile_sn,gun_num, openid,out_trade_no,charg_time, voltage,
                    current,output_voltage, output_current, current_readings
    :return:
    """
    print('Enter pile_charging_status_report', kwargs)
    pile_sn = kwargs.get("pile_sn", None)

    if pile_sn is None:
        print("pile_sn Can not Empty")
        return

    # 桩SN
    b_pile_sn = get_32_byte(pile_sn)
    # 命令
    b_command = CMD_PILE_CHARGING_STATUS
    # 枪口
    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])
    # 用户识别号
    openid = kwargs.get("openid", "")
    b_openid = get_32_byte(openid)
    # 订单号
    out_trade_no = kwargs.get("out_trade_no", "")
    if out_trade_no is None:
        print("out_trade_no can not empty....")
        return

    b_out_trade_no = get_32_byte(out_trade_no)
    # 当前充电时间
    b_charg_time = get_byte_daytime(datetime.now())
    # 当前SOC值
    cur_soc = kwargs.get("soc", 0)
    b_cur_soc = bytes([cur_soc])

    voltage = kwargs.get("voltage", 0)
    b_voltage = voltage.to_bytes(2, byteorder="big")

    current = kwargs.get("current", 0)
    b_current = current.to_bytes(2, byteorder="big")

    output_voltage = kwargs.get("output_voltage", 0)
    b_output_voltage = output_voltage.to_bytes(2, byteorder="big")

    output_current = kwargs.get("output_current", 0)
    b_output_current = output_current.to_bytes(2, byteorder="big")

    current_readings = kwargs.get("current_readings", 0)
    b_current_readings = current_readings.to_bytes(4, byteorder="big")

    b_blank = bytes(10)

    data = b''.join([b_command, b_gun_num, b_openid, b_out_trade_no, b_charg_time, b_cur_soc, b_voltage, b_current,
                     b_output_voltage, b_output_current, b_current_readings, b_blank])

    data_len = (len(data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    b_rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, b_rand, data_len, data])
    b_checksum = bytes([uchar_checksum(byte_proto_data)])
    b_reply_proto = b"".join([byte_proto_data, b_checksum, PROTOCAL_TAIL])

    client_publish(pile_sn, b_reply_proto)
    print('Leave pile_charging_status_report')


def pile_status_report(*arg, **kwargs):
    """
    说明：充电桩->服务器，状态改变时即时上报，空闲时每30S上报一次，此报文可做为充电桩与后台之间的心跳包，
        服务器接收到上报数据后，下发版本信息给充电桩
    数据区： 1字节(0x01) + 1字节(桩类型) + 2字节(固件版本号) + 1字节(枪1) + 1字节(枪2)
         + 10字节(电桩的状态详情) + 2字节(枪1温度PT-1) + 2字节(枪1温度PT-2) + 2字节(枪2温度PT-1) + 2字节(枪2温度PT-2)
         + 2字节(柜内温度PT-1) + 2字节(柜内温度PT-2) + 1字节(4G使用标志) + 1字节(4G重启次数)
         + 2字节(预约分钟数1) + 2字节(预约分钟数2) + 2字节(充电分钟数1) + 2字节(充电分钟数2)
         + 2字节(占位分钟数1) + 2字节(占位分钟数2) + 14字节（保留）
    :param arg:
    :param kwargs:
    :return:
    """
    pile_sn = kwargs.get("pile_sn", None)

    if pile_sn is None:
        return

    b_pile_sn = get_32_byte(pile_sn)
    b_command = CMD_PILE_STATUS

    pile_type = kwargs.get("pile_type", 0)      # 充电类型（1直流，2交流，3电源分配主机）
    pile_mode = kwargs.get("pile_mode", 0)      # 1 分机形式 2 整机形式
    max_gun = kwargs.get("max_gun", 0)          # 本机枪口号0-7，最多支持16个枪口或分机
    b_charg_pile_type = bytes([(pile_type << 6 & 0xff) | (pile_mode << 4 & 0xff) | (max_gun & 0xff)])
    # 固件版本
    fireware = kwargs.get('fireware', 0)
    b_fireware = get_byte_version(fireware)

    # 枪1 工作状态
    gun_one_status = kwargs.get('gun_one_status', 0)
    if gun_one_status is None or gun_one_status == 0:
        b_gun_one_status = bytes([gun_one_status])
    else:
        gun_one_code = kwargs.get('gun_one_code', 0)
        b_gun_one_status = bytes([(gun_one_status << 6 & 0xff) | (gun_one_code & 0xff)])

    # 枪2 工作状态
    gun_two_status = kwargs.get('gun_two_status', 0)
    if gun_two_status is None or gun_two_status == 0:
        b_gun_two_status = bytes([gun_two_status])
    else:
        gun_two_code = kwargs.get('gun_two_status', 0)
        b_gun_two_status = bytes([(gun_two_status << 6 & 0xff) | (gun_two_code & 0xff)])

    # 枪1 状态
    cc1_status = kwargs.get("cc1_status", 0)            # D02-D00
    cp1_status = kwargs.get("cp1_status", 0)            # D05-D03
    gun1_temp_status = kwargs.get("gun1_temp_status", 0)    # D07-D06
    b_cc_cp_temp_status1 = bytes([(cc1_status & 0xff) | (cp1_status << 3 & 0xff) | gun1_temp_status << 6 & 0xff])

    elec1_lock_status = kwargs.get("elec1_lock_status", 0)  # D09-D08
    relay1_status = kwargs.get("relay1_status", 0)          # D11-D10
    fuse1_status = kwargs.get("fuse1_status", 0)            # D13-D12
    b_lock_relay_fuse_status1 = bytes([(elec1_lock_status & 0xff) | (relay1_status << 2 & 0xff) | fuse1_status << 4 & 0xff])

    # 枪2 状态
    cc2_status = kwargs.get("cc2_status", 0)                # D18-D16
    cp2_status = kwargs.get("cp2_status", 0)                # D21-D19
    gun2_temp_status = kwargs.get("gun2_temp_status", 0)    # D23-D22
    b_cc_cp_temp_status2 = bytes([(cc2_status & 0xff) | (cp2_status << 3 & 0xff) | gun2_temp_status << 6 & 0xff])

    elec2_lock_status = kwargs.get("elec2_lock_status", 0)  # D25-D24
    relay2_status = kwargs.get("relay2_status", 0)          # D27-D26
    fuse2_status = kwargs.get("fuse2_status", 0)            # D29-D28
    b_lock_relay_fuse_status2 = bytes([(elec2_lock_status & 0xff) | (relay2_status << 2 & 0xff) | fuse2_status << 4 & 0xff])

    # 电源模块1
    power_module1 = kwargs.get("power_module1", 0)   # 2 byte
    b_power_module1 = power_module1.to_bytes(2, byteorder="big")
    # 电源模块2
    power_module2 = kwargs.get("power_module2", 0)   # 2 byte
    b_power_module2 = power_module2.to_bytes(2, byteorder="big")
    # 柜内温度状态
    cabinet_temp1_status = kwargs.get("cabinet_temp1_status", 0)
    cabinet_temp2_status = kwargs.get("cabinet_temp2_status", 1)
    spd_status = kwargs.get("spd_status", 1)
    emerg_stop_status = kwargs.get("emerg_stop_status", 0)
    water_status = kwargs.get("water_status", 0)
    door_status = kwargs.get("door_status", 0)
    power_fail_status = kwargs.get("power_fail_status", 0)
    elec_leak_status = kwargs.get("elec_leak_status", 0)
    b_cabinet_status = bytes([(cabinet_temp1_status & 0xff) | (cabinet_temp2_status << 1 & 0xff) | (spd_status << 2 & 0xff) | emerg_stop_status << 3 & 0xff
                              | water_status << 4 & 0xff | door_status << 5 & 0xff | power_fail_status << 6 &0xff
                              | elec_leak_status << 6 & 0xff])
    # 枪1 PT-1温度
    gun1_temp1 = kwargs.get("gun1_temp1", 0)
    b_gun1_temp1 = gun1_temp1.to_bytes(2, byteorder="big")
    # 枪1 PT-2温度
    gun1_temp2 = kwargs.get("gun1_temp2", 0)
    b_gun1_temp2 = gun1_temp2.to_bytes(2, byteorder="big")
    # 枪2 PT-1温度
    gun2_temp1 = kwargs.get("gun2_temp1", 0)
    b_gun2_temp1 = gun2_temp1.to_bytes(2, byteorder="big")
    # 枪2 PT-2温度
    gun2_temp2 = kwargs.get("gun2_temp2", 0)
    b_gun2_temp2 = gun2_temp2.to_bytes(2, byteorder="big")
    # 柜内温度PT-1
    cabinet_temp1 = kwargs.get("cabinet_temp1", 0)
    b_cabinet_temp1 = cabinet_temp1.to_bytes(2, byteorder="big")
    # 柜内温度PT-2
    cabinet_temp2 = kwargs.get("cabinet_temp2", 0)
    b_cabinet_temp2 = cabinet_temp2.to_bytes(2, byteorder="big")
    # 4G,ETH使用标志
    symbol_4g = kwargs.get("symbol_4g", 0)
    symbol_eth = kwargs.get("symbol_eth", 0)
    b_symbol_4g_eth = bytes([symbol_4g << 7 & 0xff | symbol_eth << 6 & 0xff])
    # 重启次数
    restart_nums = kwargs.get("restart_nums", 0)
    b_restart_nums = bytes([restart_nums])

    subscribe_min1 = kwargs.get("subscribe_min1", 0)
    recharge_min1 = kwargs.get("recharge_min1", 0)
    occupy_min1 = kwargs.get("occupy_min1", 0)
    b_subscribe_min1 = subscribe_min1.to_bytes(2, byteorder="big")
    b_recharge_min1 = recharge_min1.to_bytes(2, byteorder="big")
    b_occupy_min1 = occupy_min1.to_bytes(2, byteorder="big")

    subscribe_min2 = kwargs.get("subscribe_min2", 0)
    recharge_min2 = kwargs.get("recharge_min2", 0)
    occupy_min2 = kwargs.get("occupy_min2", 0)
    b_subscribe_min2 = subscribe_min2.to_bytes(2, byteorder="big")
    b_recharge_min2 = recharge_min2.to_bytes(2, byteorder="big")
    b_occupy_min2 = occupy_min2.to_bytes(2, byteorder="big")

    b_data = b''.join([b_command, b_charg_pile_type, b_fireware, b_gun_one_status, b_gun_two_status, b_cc_cp_temp_status1,
                     b_lock_relay_fuse_status1, b_cc_cp_temp_status2, b_lock_relay_fuse_status2, b_power_module1,
                     b_power_module2, b_cabinet_status, b_gun1_temp1, b_gun1_temp2, b_gun2_temp1, b_gun2_temp2,
                     b_cabinet_temp1, b_cabinet_temp2, b_symbol_4g_eth, b_restart_nums, b_subscribe_min1,
                     b_subscribe_min2, b_recharge_min1, b_recharge_min2, b_occupy_min1,  b_occupy_min2])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    rand = bytes([random.randint(0, 2)])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])

    b_reply_proto = b"".join([byte_proto_data, checksum, PROTOCAL_TAIL])

    client_publish(pile_sn, b_reply_proto)


# 处理版本信息
def client_version_info_handler(topic, byte_msg):
    """
    处理服务端的版本信息
    :param topic:
    :param byte_msg:
    :return:
    """
    if len(byte_msg) < 40:
        print("protocol data is wrong")
        return

    data_nums = get_data_nums(byte_msg)

    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    print('电桩编号SN:', pile_sn)
    # 时间
    high_year = byte2integer(byte_msg, 38, 39)
    low_year = byte2integer(byte_msg, 39, 40)
    month = byte2integer(byte_msg, 40, 41)
    day = byte2integer(byte_msg, 41, 42)
    hour = byte2integer(byte_msg, 42, 43)
    minute = byte2integer(byte_msg, 43, 44)
    second = byte2integer(byte_msg, 44, 45)
    syncDate = '{0}{1}-{2}-{3} {4}:{5}:{6}'.format(high_year, low_year, month, day, hour, minute, second)
    print(syncDate)

    dc_version = byte2integer(byte_msg, 45, 47)    # 直流版本号
    dc_ver_min = dc_version & 0xFF       # D7-D0位：版本小数位
    dc_ver_max = dc_version >> 8 & 0xFF    # D15-D8位：版本整数位
    print('直流版本号:{}.{}'.format(dc_ver_max, dc_ver_min))

    ac_version = byte2integer(byte_msg, 47, 49)
    ac_ver_min = ac_version & 0xFF
    ac_ver_max = ac_version >> 8 & 0xFF
    print('交流版本号:{}.{}'.format(ac_ver_max, ac_ver_min))

    power_distrib_version = byte2integer(byte_msg, 49, 51)
    power_ver_min = power_distrib_version & 0xFF
    power_ver_max = power_distrib_version >> 8 & 0xFF
    print('电源分配主版本号:{}.{}'.format(power_ver_max, power_ver_min))


def client_configure_pile_params(topic, byte_msg):
    """
    充电桩接收到服务器发来的配置参数指令，解析并处理后，返回报文
    :param topic:
    :param byte_msg:
    :return:
    """
    logging.info("Enter client_configure_pile_params function")
    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    print('充电桩SN:', pile_sn)
    # 扩展枪2SN
    extend_sn = byte_msg[38:70].decode('utf-8').lstrip('\000')
    print('扩展SN:', extend_sn)
    # 运营属性
    business_mode = byte_msg[70]
    print('运营属性:', business_mode)
    # 枪1，2 二维码
    gun_qr_code1 = byte_msg[71:199].decode('utf-8').lstrip('\000')
    gun_qr_code2 = byte_msg[199:327].decode('utf-8').lstrip('\000')
    print('枪1，2 二维码:', gun_qr_code1, gun_qr_code2)
    # 单枪最大输出电压 单枪最小输出电压 单枪最大输出电流 单枪最小输出电流
    gun_max_voltage = byte2integer(byte_msg, 327, 329)
    gun_min_voltage = byte2integer(byte_msg, 329, 331)
    gun_max_current = byte2integer(byte_msg, 331, 333)
    gun_min_current = byte2integer(byte_msg, 333, 335)
    print("单枪电流电压:", gun_max_voltage, gun_min_voltage, gun_max_current, gun_min_current)

    # 输出限小电流启用
    output_restrict = byte2integer(byte_msg, 335, 336)
    low_restrict = output_restrict >> 7 & 0x01
    low_offset = output_restrict >> 6 & 0x01
    subscribe_status = output_restrict >> 5 & 0x01
    occupy_status = output_restrict >> 4 & 0x01
    print("输出限小电流:", low_restrict, low_offset, subscribe_status, occupy_status)

    # 限制输出小电流值 小电流补偿每分钟 预约费每5分钟 占位费每5分钟
    low_cur_value = byte2integer(byte_msg, 336, 338) * 0.1
    low_offset_value = byte2integer(byte_msg, 338, 340) * 0.1
    subscribe_fee = byte2integer(byte_msg, 340, 342) * 0.01
    occupy_fee = byte2integer(byte_msg, 342, 344) * 0.01
    print("限制输出小电流值:", low_cur_value, low_offset_value, subscribe_fee, occupy_fee)

    # 离线充电价格0点后 离线充电价格1点后 离线充电价格2点后 离线充电价格3-22点后  离线充电价格23点后
    offline_price = byte_msg[344: 392]
    dict_offline_price = {int(i/2): int.from_bytes(offline_price[i:i+2] * 0.01, byteorder="big") for i in range(0, len(offline_price), 2) }

    print("离线充电价格:", dict_offline_price)
    byte_msg[37] = CMD_PILE_PARAMS
    client_publish(pile_sn, byte_msg)  # 回复报文
    logging.info("Leave client_configure_pile_params function")


def client_request_pile_params_handler(topic, byte_msg):
    """
    接收服务端的参数查询指令,回复电桩参数
    :param topic:
    :param byte_msg:
    :return:
    """
    logging.info("Enter client_request_pile_params_handler function")
    data = {}
    client_reply_pile_params_request(**data)
    logging.info("Enter client_request_pile_params_handler function")


def client_reply_pile_params_request(*args, **kwargs):
    """
    6、充电桩向服务器上报桩参数(client--->server)
    说明：充电桩->服务器，充电桩回复服务器命令（0x82和0x83）回复此报文，格式除命令外与0x83命令一致（480字节）。
   数据区：命令号0x03（1字节）+扩展枪2SN（32字节）+运营属性（1字节）+枪1对应的二维码（128字节）+枪2对应的二维码（128字节）+单枪最大输出电压（2字节）
   +单枪最小输出电压（2字节）+单枪最大输出电流（2字节）+单枪最小输出电流（2字节）+输出限小电流启用（1字节）+限制输出小电流值（2字节）+小电流补偿每分钟（2字节）
   +预约费每5分钟（2字节）+占位费每5分钟（2字节）+离线充电价格0点后（2字节）+离线充电价格1点后（2字节）+离线充电价格2点后（2字节）+ 离线充电价格3-22点后（40字节）
   +离线充电价格23点后（2字节）+保留（24字节）
    :param kwargs: pile_sn, extend_sn,pile_type, pile_mode, max_gun, business_mode, qr_code1 , qr_code2,
                    gun_max_voltage, gun_min_voltage, gun_max_current, gun_min_current, low_restrict,
                    low_offset, subscribe_status, occupy_status, low_cur_value, low_offset_value,
                    subscribe_fee, occupy_fee, off_line_price
    :return:
    """
    logging.info("Enter client_reply_pile_params_request function")

    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        logging.info("Device SN Can not Empty")
        return
    b_pile_sn = get_32_byte(pile_sn)

    b_command = CMD_SET_PILE_PARARMS

    extend_sn = kwargs.get("extend_sn", "")
    b_extend_sn = get_32_byte(extend_sn)  # 扩展SN号

    # 桩类型
    pile_type = kwargs.get("pile_type", 0)   # 01直流，10交流，11电源分配主机 D7-D6位
    pile_mode = kwargs.get("pile_mode", 0)   # 01分机形式，每个分机独立，10整机形式 D5-D4位
    max_gun = kwargs.get("max_gun", 0)     # 本机枪口号0-7，最多支持8个枪口或分机 D3-D0位
    b_charg_pile_type = bytes([(pile_type << 6 & 0xff) | (pile_mode << 4 & 0xff) | (max_gun & 0xff)])

    # 运营模式
    business_mode = kwargs.get("business_mode", 1)
    b_business_mode = bytes([business_mode])

    # 枪的二维码
    qr_code1 = kwargs.get("qr_code1", "")
    qr_code2 = kwargs.get("qr_code2", "")
    b_qr_code1 = get_32_byte(qr_code1, b_len=128)
    b_qr_code2 = get_32_byte(qr_code2, b_len=128)

    # 单枪电压电流参数(单枪最大输出电压, 单枪最小输出电压, 单枪最大输出电流,单枪最小输出电流)
    gun_max_voltage = kwargs.get("gun_max_voltage", 0)
    gun_min_voltage = kwargs.get("gun_min_voltage", 0)
    gun_max_current = kwargs.get("gun_max_current", 0)
    gun_min_current = kwargs.get("gun_min_current", 0)

    b_gun_max_voltage = gun_max_voltage.to_bytes(2, byteorder="big")
    b_gun_min_voltage = gun_min_voltage.to_bytes(2, byteorder="big")
    b_gun_max_current = gun_max_current.to_bytes(2, byteorder="big")
    b_gun_min_current = gun_min_current.to_bytes(2, byteorder="big")

    # 输出限小电流启用
    low_restrict = kwargs.get("low_restrict", 0)
    low_offset = kwargs.get("low_offset", 0)
    subscribe_status = kwargs.get("subscribe_status", 0)
    occupy_status = kwargs.get("occupy_status", 0)

    b_low_current_limit = bytes([low_restrict << 7 & 0xff | low_offset << 6 & 0xff | subscribe_status << 5 & 0xff | occupy_status << 4 & 0xff])

    # 限制输出小电流值
    low_cur_value = kwargs.get("low_cur_value", 0)
    b_low_cur_value = low_cur_value.to_bytes(2, byteorder="big")
    # 小电流补偿每分钟
    low_offset_value = kwargs.get("low_offset_value", 0)
    b_low_offset_value = low_offset_value.to_bytes(2, byteorder="big")
    # 预约费每5分钟
    subscribe_fee = kwargs.get("subscribe_fee", 0)
    b_subscribe_fee = subscribe_fee.to_bytes(2, byteorder="big")
    # 占位费每5分钟
    occupy_fee = kwargs.get("occupy_fee", 0)
    b_occupy_fee = occupy_fee.to_bytes(2, byteorder="big")
    # 离线充电价格24个小时的价格
    off_line_price = kwargs.get("off_line_price", {})
    offline_price_list = []
    for value in off_line_price.values():
        offline_price_list.append(value.to_bytes(2, byteorder="big"))

    b_offline_price = b''.join(offline_price_list)

    b_data = b''.join([b_command, b_extend_sn, b_charg_pile_type, b_business_mode, b_qr_code1, b_qr_code2,
                        b_gun_max_voltage, b_gun_min_voltage, b_gun_max_current, b_gun_min_current,
                        b_low_current_limit, b_low_cur_value, b_low_offset_value, b_subscribe_fee, b_occupy_fee,
                        b_offline_price])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    rand = bytes([random.randint(0, 2)])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])

    b_reply_proto = b"".join([byte_proto_data, checksum, PROTOCAL_TAIL])

    client_publish(pile_sn, b_reply_proto)

    logging.info("Leave client_reply_pile_params_request function")


# 回复充电命令
def client_reply_charging_cmd(topic, byte_msg):
    """
    #8、充电桩回复充电指令 说明：充电桩->服务器，此命令回复时间较长，服务器端超时判断为150S（80字节）
    数据区: 命令号0x04（1字节）+ 枪口号（1字节）+ 用户识别号（32字节）+ 订单号（32字节）+ 命令执行结果（1字节）+ 保留（13字节）
    充电桩回复服务端发来的充电命令0x84
    解析充电命令后，回复
    :param byte_msg:
    :return:
    """
    if len(byte_msg) < 80:
        print("protocol data is wrong")
        return

    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    g_pile_sn = pile_sn
    print('电桩编号SN:', pile_sn)
    # 枪口号

    gun_num = byte2integer(byte_msg, 38, 39)
    global g_gun_num, g_out_trade_no, g_openid
    g_gun_num = gun_num
    print('枪口号:', gun_num, g_gun_num)
    charging_type = byte2integer(byte_msg, 39, 40)    # 充电类型 和预约时间
    charg_type = charging_type >> 7 & 0xff  #类型  D7：1预约，0即时
    print('充电类型：', charg_type)
    subscribe_time = charging_type & 0x7f
    print('预约时间：', subscribe_time)
    charg_plans = byte2integer(byte_msg, 40, 42)        # 充电策略（2字节）
    print('充值策略:', bin(charg_plans))
    charg_plans_value = byte2integer(byte_msg, 42, 46)
    print('充值策略值:', charg_plans_value)
    # 用户识别号

    openid = byte_msg[46:78].decode('utf-8').strip('\000')
    g_openid = openid
    print('用户识别号:', openid, g_openid)
    # 订单

    out_trade_no = byte_msg[78:110].decode('utf-8').strip('\000')
    g_out_trade_no = out_trade_no
    print('订单号:', out_trade_no, g_out_trade_no)
    # 同步时间
    high_year = byte2integer(byte_msg, 110, 111)
    low_year = byte2integer(byte_msg, 111, 112)
    month = byte2integer(byte_msg, 112, 113)
    day = byte2integer(byte_msg, 113, 114)
    hour = byte2integer(byte_msg, 114, 115)
    minute = byte2integer(byte_msg, 115, 116)
    second = byte2integer(byte_msg, 116, 117)
    syncDate = '{0}{1}-{2}-{3} {4}:{5}:{6}'.format(high_year, low_year, month, day, hour, minute, second)
    print('同步时间:', syncDate)
    # ------------------------------------------------
    b_command = CMD_PILE_CHARG_REPLY    # 回复充电命令
    b_gun_num = bytes([gun_num])    # 枪口
    b_openid = get_32_byte(openid)  # 用户标识
    b_out_trade_no = get_32_byte(out_trade_no)      # 订单号
    b_result_cmd = bytes([1])           # 执行结果标识 1准备充电作业，0充电枪未连接等符充电作业

    b_data = b''.join([b_command, b_gun_num, b_openid, b_out_trade_no, b_result_cmd])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    rand = bytes([0])
    b_pile_sn = get_32_byte(pile_sn)

    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])

    b_reply_proto = b"".join([byte_proto_data, checksum, PROTOCAL_TAIL])

    client_publish(pile_sn, b_reply_proto)
    # 发送车辆信息
    time.sleep(3)
    car_info_data = {
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "openid": openid,
        "out_trade_no": out_trade_no,
        "protocol": random.randint(0, 3),
        "vin_code": str(random.randint(1000, 2000000)),
        "max_single_voltage": random.randint(100, 200),
        "max_current": random.randint(10, 200),
        "total_capacity": random.randint(10, 200),
        "max_voltage": random.randint(150, 220),
        "max_temp": random.randint(10, 60),
        "begin_soc": random.randint(10, 20),
        "begin_reading": 0,
    }

    pile_report_car_info(**car_info_data)


def client_stop_charging_handler(topic, byte_msg):
    """
    充电桩处理服务器发来的停止充电命令,并且回复停充指令.
    :param topic:
    :param byte_msg:
    :return:
    """
    if len(byte_msg) < 40:
        print("protocol data is wrong")
        return

    data_nums = get_data_nums(byte_msg)

    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    print('电桩编号SN:', pile_sn)
    # 枪口号
    gun_num = byte_msg[38]
    print('枪口号:', gun_num)
    # 用户识别号
    openid = byte_msg[39:71].decode('utf-8').strip('\000')
    # 订单
    out_trade_no = byte_msg[71:103].decode('utf-8').strip('\000')
    print('订单号:', out_trade_no)

    consum_money = byte2integer(byte_msg, 103, 107)
    print('消费金额:', consum_money)

    total_reading = byte2integer(byte_msg, 107, 111)
    print('总充电量:', total_reading)

    stop_code = byte_msg[111]
    print('停止标记:', stop_code)
    ret_cur_readings = 100
    if stop_code == 0:
        return_stop_code = 1
    else:
        return_stop_code = 0

    data = {
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "openid": openid,
        "current_reading": ret_cur_readings,
        "out_trade_no": out_trade_no,
        "stop_code": return_stop_code,
        "fault_code": 0,
    }

    pile_stop_charging_report(**data)


# 0x07
def pile_stop_charging_report(*arg, **kwargs):
    """
     13、充电桩停止充电上报(client)
    说明：充电桩->服务器，充电桩主动上报停止充电或回复0x86命令（72字节）。
    数据区：命令号0x07（1字节）+枪口号（1字节）+用户识别号（32字节）+订单号（32字节）+停止充电回复代码（1字节）+故障代码（1字节）+保留（4字节）
    :param arg:
    :param kwargs:
    :return:
    """
    logging.info("Enter pile_stop_charging_report function")

    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        logging.info("Device SN Can not be Empty")
        return

    b_pile_sn = get_32_byte(pile_sn)

    out_trade_no = kwargs.get("out_trade_no", None)
    if out_trade_no is None:
        logging.info("Order Can not be Empty")
        return
    b_out_trade_no = get_32_byte(out_trade_no)

    openid = kwargs.get("openid", "")
    b_openid = get_32_byte(openid)

    b_command = CMD_PILE_STOP_CHARGING     # 回复停止充电命令

    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])

    current_reading = kwargs.get("current_reading", 0)
    b_current_reading = current_reading.to_bytes(4, byteorder="big")

    stop_code = kwargs.get("stop_code", 0)
    b_stop_code = bytes([stop_code])

    fault_code = kwargs.get("falut_code", 0)
    b_fault_code = bytes([fault_code])

    b_blank = bytes(8)

    b_data = b''.join([b_command, b_gun_num, b_openid, b_out_trade_no, b_current_reading, b_stop_code, b_fault_code, b_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    b_rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, b_rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])

    b_reply_proto = b"".join([byte_proto_data, checksum, PROTOCAL_TAIL])
    global g_out_trade_no
    g_out_trade_no = None

    client_publish(pile_sn, b_reply_proto)

    logging.info("leave pile_stop_charging_report function")


def client_force_stop_charging_handler(topic, byte_msg):
    pass


def client_publish(pile_sn, data):
    topic = '/{0}/pub'.format(pile_sn)
    client.publish(topic, data)


def decrypt_message(byte_msg):
    """
    报文解密
    :param byte_msg:
    :return:
    """
    return byte_msg


def is_legal_message(byte_msg):
    """
    # 协议是否合法
    # 取头尾各两个字节，判断协议是否正确
    :param byte_msg:
    :return:
    """
    byte_data = byte_msg

    head_flag = bytes.hex(byte_data[0:2])
    tail_flag = bytes.hex(byte_data[-2:])
    print(head_flag, '==', tail_flag)
    if head_flag.upper() == 'AAAA' and tail_flag == "5555":
        # 去除转义符
        byte_data = byte_data.replace(b'\xaa\x7e', b'\xaa')
        byte_data = byte_data.replace(b'\x55\x7e', b'\x55')
        byte_data = byte_data.replace(b'\x7e\x7e', b'\x7e')
        #  校验数据
        remote_check_sum = int(bytes.hex(byte_data[-3:-2]), 16)
        local_check_sum = uchar_checksum(byte_data[0:-3])
        if remote_check_sum == local_check_sum:  # 数据校验
            return byte_data
        else:
            return None
    else:
        return None


# 工具函数开始
def get_mqtt_param(product_key, device_name, device_secret):
    ProductKey = product_key
    ClientId = device_name
    DeviceName = device_name
    DeviceSecret = device_secret

    signmethod = "hmacsha1"
    us = math.modf(time.time())[0]
    ms = int(round(us * 1000))
    timestamp = str(ms)
    data = "".join(("clientId", ClientId, "deviceName", DeviceName,
                    "productKey", ProductKey, "timestamp", timestamp))

    ret = hmac.new(bytes(DeviceSecret, encoding='utf-8'), bytes(data, encoding='utf-8'), hashlib.sha1).hexdigest()
    sign = ret
    client_id = "".join((ClientId, "|securemode=3", ",signmethod=", signmethod, ",timestamp=", timestamp, "|"))
    username = "".join((DeviceName, "&", ProductKey))
    password = sign
    return client_id, username, password


def get_data_nums(byte_msg):
    """
    获得数据区的字节长度
    :param byte_msg:
    :return:
    """
    b_nums = byte_msg[35:37]
    nums = int(bytes.hex(b_nums), 16)
    return nums


def get_pile_sn(byte_msg):
    """
    充电桩sn编码
    :param byte_msg:
    :return: 充电桩sn编码
    """
    if len(byte_msg) > 20:
        pile_sn = byte_msg[2:34].decode('utf-8').strip('\000')
        return pile_sn
    else:
        return ""


def get_32_byte(data, b_len=32):
    b_data = data.encode("utf-8")
    blank_byte = bytes(b_len - len(b_data))
    return b''.join([b_data, blank_byte])


def set_hex_format(data, nums):
    hex_str = binascii.hexlify(data.encode())
    return hex_str.decode().zfill(nums)


# 字节转整数
def byte2integer(byte_msg, start_pos, end_pos):
    return int.from_bytes(byte_msg[start_pos:end_pos], byteorder="big")
    # return int(bytes.hex(byte_msg[start_pos:end_pos]), 16)


def get_byte_daytime(dtime=datetime.now()):
    """
    返回七字节的时间
    :param dtime:b
    :return:
    """
    high_year, low_year = divmod(dtime.year, 100)
    b_high_year = bytes([high_year])
    b_low_year = bytes([low_year])
    b_month = bytes([dtime.month])
    b_day = bytes([dtime.day])
    b_hour = bytes([dtime.hour])

    b_minute = bytes([dtime.minute])
    b_second = bytes([dtime.second])
    ret_value = b''.join([b_high_year, b_low_year, b_month, b_day, b_hour, b_minute, b_second])
    return ret_value


def char_checksum(data, byteorder='big'):
    """
    char_checksum 按字节计算校验和。每个字节被翻译为带符号整数
    @param data: 字节串
    @param byteorder: 大/小端
    """
    length = len(data)
    checksum = 0
    for i in range(0, length):
        x = int.from_bytes(data[i:i+1], byteorder, signed=True)
        if x > 0 and checksum > 0:
            checksum += x
            if checksum > 0x7F:  # 上溢出
                checksum = (checksum & 0x7F) - 0x80  # 取补码就是对应的负数值
        elif x < 0 and checksum < 0:
            checksum += x
            if checksum < -0x80:  # 下溢出
                checksum &= 0x7F
        else:
            checksum += x  # 正负相加，不会溢出

    return checksum


def uchar_checksum(data, byteorder='big'):
    """
    char_checksum 按字节计算校验和。每个字节被翻译为无符号整数
    @param data: 字节串
    @param byteorder: 大/小端
    """
    length = len(data)
    checksum = 0
    for i in range(0, length):
        checksum += int.from_bytes(data[i:i+1], byteorder, signed=False)
        checksum &= 0xFF  # 强制截断

    return checksum


def get_byte_version(version):
    """
    获取版本的字节形式
    :param version:
    :return:
    """
    ver = version
    if not isinstance(ver, str):
        ver = str(ver)

    ver_list = ver.split('.')
    if len(ver_list) == 2:
        high_ver = int(ver_list[0])
        low_ver = int(ver_list[1])
    else:
        high_ver = int(ver_list[0])
        low_ver = 0

    return b''.join([bytes([high_ver]), bytes([low_ver])])
# 工具函数结束


if __name__ == "__main__":

    client_id = DEVICENAME
    username = USERNAME
    password = PASSWORD
    port = 1883
    # 初始化客户端
    mqtt.Client.connected_flag = False
    mqtt.Client.bad_connection_flag = False
    mqtt.Client.topic_ack = []

    # 连接到mqtt broker
    print("Connecting to broker ", MQTT_URL)
    try:
        client = mqtt.Client(client_id=client_id, clean_session=False)
        client.username_pw_set(username, password)
        # 指定事件回调函数
        client.on_message = on_message
        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_disconnect = on_disconnect
        client.on_log = on_log
        ret = client.connect(MQTT_URL, port, 60)
    except Exception as ex:
        print("Can't Connected", ex)
        sys.exit(1)

    # Continue monitoring the incoming messages for subscribed topic
    def Quit(signum, frame):
        client.disconnect()
        client.loop_stop()
        sys.exit()

    signal.signal(signal.SIGINT, Quit)
    signal.signal(signal.SIGTERM, Quit)

    client.loop_start()
    current_readings = 0
    while True:
        time.sleep(10)
        data = {
            "pile_sn": DEVICENAME,
            "gun_num": g_gun_num,
            "out_trade_no": g_out_trade_no,
            "openid": g_openid,
            "soc": random.randint(1, 100),
            "current": random.randint(10, 20),
            "voltage": random.randint(100, 200),
            "output_voltage": random.randint(100, 200),
            "output_current": random.randint(10, 200),
            'current_readings': current_readings,
        }
        if g_out_trade_no is not None:
            pile_charging_status_report(**data)
            current_readings += 5
            if current_readings == 50:
                stop_data = {
                    "pile_sn": DEVICENAME,
                    "gun_num": g_gun_num,
                    "openid": g_openid,
                    "current_reading": current_readings,
                    "out_trade_no": g_out_trade_no,
                    "stop_code": 0,
                    "fault_code": 0,
                }
                pile_stop_charging_report(**stop_data)

    client.loop_stop()

    # client.loop_forever()
