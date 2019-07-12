# coding=utf-8
import base64
import json
import random
from datetime import  datetime
from chargingstation import settings

__author__ = 'Administrator'


from .utils import get_32_byte, get_byte_daytime, get_pile_sn, byte2integer, uchar_checksum, send_cmd, get_data_nums
from codingmanager.constants import *


# 7 (0x84)
def server_send_charging_cmd(*args, **kwargs):
    """
    服务器向充电桩下发充电指令 命令号0x84
    命令号0x84（1字节） + 枪口号（1字节）+ 充电类型（1字节）+ 充电策略（2字节）+ 充电策略值（4字节）+ 用户识别号（32字节）+ 订单号（32字节）
    + 同步时间（7字节） + 保留（8字节）
    此函数由用户扫描缴费调用，通过二维码的pile_sn 和 gun_nums确定后台的数据内容
    :param args:
    :param kwargs: pile_sn, gun_nums, openid, out_trade_no, product_key, device_name
    :return:
    """
    pile_sn = get_32_byte(kwargs.get("pile_sn"))

    command = CMD_SEND_CHARGING
    gun_num = bytes([int(kwargs.get("gun_num"))])
    charging_type = bytes([0])    # 充电类型
    charging_policy = (0).to_bytes(2, byteorder='big')
    charging_policy_value = (0).to_bytes(4, byteorder='big')
    openid = get_32_byte(kwargs.get("openid"))
    out_trade_no = get_32_byte(kwargs.get("out_trade_no"))
    send_time = get_byte_daytime(datetime.now())

    data = b''.join([command, gun_num, charging_type, charging_policy, charging_policy_value, openid, out_trade_no, send_time])

    data_len = (len(data)).to_bytes(2, byteorder='big')
    rand = bytes([random.randint(0, 2)])
    byte_proto_data = b"".join([PROTOCAL_HEAD, pile_sn, rand, data_len, data])
    checksum = bytes([uchar_checksum(byte_proto_data)])

    reply_proto = b"".join([byte_proto_data, checksum, PROTOCAL_TAIL])
    product_key = kwargs.get("product_key", None)
    device_name = kwargs.get("device_name", None)
    if product_key is None:
        product_key = settings.PRODUCT_KEY
    if device_name is None:
        device_name = kwargs.get("pile_sn")

    response = send_cmd(product_key, device_name, base64.b64encode(reply_proto), 5000)
    ret_data = response.decode("utf-8")
    json_data = json.loads(ret_data)
    if json_data.get("Success"):
        byte_msg = base64.b64decode(json_data.get("PayloadBase64Byte"))
        pile_reply_charging_cmd_handler(byte_msg)       # 处理充电回复命令
    else:
        print(json_data)


# 8 (0x04)
def pile_reply_charging_cmd_handler(byte_msg):
    """
    充电桩回复充电指令 命令号0x04
    :param byte_msg:
    :return:
    """
    if len(byte_msg) < 40:
        print("protocol data is wrong")
        return
    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    print("电桩编码SN:", pile_sn)
    # 枪口号
    gun_num = byte2integer(byte_msg, 38, 39)
    print("枪口:", gun_num)
    # 用户识别号
    openid = byte_msg[39:71].decode('utf-8').lstrip('\000')
    print("用户标识:", openid)
    # 订单
    out_trade_no = byte_msg[71:103].decode('utf-8').lstrip('\000')
    print("订单号:", out_trade_no)
    # 命令执行结果(充电状态)
    charg_status = byte2integer(byte_msg, 103, 104)
    print("命令执行结果:", charg_status)
    # 保留（13字节）


# 12 (0x86)
def server_send_stop_charging_cmd(*args, **kwargs):
    """
    12、服务器主动下发停止充电
     说明：服务器->充电桩，服务器主动向充电桩发送停止充电指令（72字节）。
     数据区：命令号0x86（1字节）+枪口号（1字节）+用户识别号（32字节）+订单号（32字节）+保留（6字节）
    :param args:
    :param kwargs: pile_sn, gun_nums, openid, out_trade_no, product_key, device_name
    :return:
    """
    print("Enter server_send_stop_charging_cmd function")

    product_key = kwargs.get("product_key")
    if product_key is None:
        print("product_key can not be empty")
        return

    device_name = kwargs.get("device_name")
    if device_name is None:
        print("device_name can not be empty")
        return

    out_trade_no = kwargs.get("out_trade_no", None)
    if out_trade_no is None:
        print("Order Can Not Be Empty")
        return

    # 订单号
    b_out_trade_no = get_32_byte(out_trade_no)
    # 命令
    b_command = CMD_SEND_STOP_CHARG
    # 枪口号
    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])
    # 用户识别号
    openid = kwargs.get("openid", "")
    b_openid = get_32_byte(openid)

    data = b''.join([b_command, b_gun_num, b_openid, b_out_trade_no])

    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        pile_sn = device_name

    b_pile_sn = get_32_byte(pile_sn)

    data_len = (len(data)).to_bytes(2, byteorder='big')
    rand = bytes([random.randint(0, 2)])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, data])
    checksum = bytes([uchar_checksum(byte_proto_data)])

    reply_proto = b"".join([byte_proto_data, checksum, PROTOCAL_TAIL])
    print(reply_proto)

    response = send_cmd(product_key, device_name, base64.b64encode(reply_proto))
    ret_data = response.decode("utf-8")
    json_data = json.loads(ret_data)
    if json_data.get("Success"):
        print(json_data.get("PayloadBase64Byte"), json_data.get("MessageId"))
        msg_str = base64.b64decode(json_data.get("PayloadBase64Byte")).decode("utf-8")
        print(msg_str)
    else:
        print(json_data)

    print("Leave server_send_stop_charging_cmd function")