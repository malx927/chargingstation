# coding=utf-8
import decimal

import os
import random
import sys
import redis
import signal
import datetime
import logging

import paho.mqtt.client as mqtt

from django.db.models import F, Sum, DecimalField

# logging.basicConfig(level=logging.INFO, filename='./logs/chargingstation.log',
#                     format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s', filemode='a')
from echargenet.utils import get_order_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
# 导入django model
BASEDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASEDIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'chargingstation.settings'
import django
django.setup()

from django.conf import settings
from stationmanager.models import ChargingPile, ChargingGun,  ChargingPrice
from codingmanager.constants import *
from chargingorder.utils import uchar_checksum, byte2integer, get_pile_sn, get_32_byte, get_byte_daytime, \
    get_data_nums, get_byte_version, get_datetime_from_byte, message_escape, save_charging_cmd_to_db, \
    send_data_to_client, user_account_deduct_money, user_update_pile_gun, get_byte_date, create_oper_log, get_fault_code
from codingmanager.models import FaultCode
from chargingorder.models import OrderRecord, Order,  OrderChargDetail, ChargingStatusRecord, \
    ChargingCmdRecord
from wxchat.models import UserInfo
from echargenet.tasks import notification_start_charge_result, notification_stop_charge_result
from wxchat.utils import send_charging_start_message_to_user
from cards.models import ChargingCard
from stationmanager.signals import update_operator_info
from stationmanager.signals import operator_info_init
from stationmanager.signals import operator_info_delete
from stationmanager.signals import update_station_info
from stationmanager.signals import station_info_delete
from stationmanager.signals import update_equipment_info
from stationmanager.signals import equipment_info_delete
from stationmanager.signals import update_connector_info
from stationmanager.signals import connector_info_delete


PRODUCTKEY = ''
DEVICENAME = 'server_main'

SUB_TOPIC = 'sub'
PUB_TOPIC = 'pub'


# 更新充电桩订阅状态
def update_pile_sub_status(topic, status):
    kwargs = {
        "sub_status": status,
        "sub_time": datetime.datetime.now()
    }
    ChargingPile.objects.filter(pile_sn=topic).update(**kwargs)


# 取消所有订阅状态
def unsubscribe_all():
    ChargingPile.objects.filter(sub_status=True).update(sub_status=False, sub_time=datetime.datetime.now())


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
        try:
            topic = '/+/{}'.format(PUB_TOPIC)
            r = client.subscribe(topic, 0)
            if r[0] == 0:
                logging.info("subscribed to topic "+str(topic)+" return code" + str(r))
                client.topic_ack.append([topic, r[1], 0])
            else:
                logging.warning("error on subscribing " + str(r) + ":" + topic)
        except Exception as ex:
            logging.warning("error on subscribe"+str(ex) + ":" + topic)
    else:
        logging.warning("Bad connection Returned code="+str(rc))
        client.bad_connection_flag = True


# 收到订阅消息回调函数
def on_message(client, userdata, msg):
    # 判断报文是否正确
    if len(msg.payload) <= 40:
        logging.warning("长度小于40：{}".format(msg.payload))
        return
    ret_data = is_legal_message(msg.payload)
    # # 报文解密
    decrypt_data = decrypt_message(ret_data)
    # # 报文调度
    message_dispatch(msg.topic, decrypt_data)


def server_publish(pile_sn, data):
    topic = '/{0}/{1}'.format(pile_sn, SUB_TOPIC)
    # logging.info('{}:{}'.format(topic, data))
    client.publish(topic, data)


def message_dispatch(topic, byte_msg):
    """
    分发报文
    :param topic:
    :param byte_msg:
    :return:
    """
    logging.info('************************enter message_dispach*******************************')

    byte_command = byte_msg[37:38]

    if byte_command == CMD_PILE_STATUS:     # 充电桩状态上报
        pile_status_handler_v12(topic, byte_msg)

    elif byte_command == CMD_CARD_CHARGING_REQUEST:   # 储值卡充电请求'0x83'
        pile_card_charging_request_hander(topic, byte_msg)

    elif byte_command == CMD_PILE_CHARG_REPLY:   # 充电桩回复充电指令 '\x04'
        pile_reply_charging_cmd_handler(topic, byte_msg)

    elif byte_command == CMD_PILE_CAR_INFO:   # 充电桩上报车辆信息
        pile_report_car_info_handler(topic, byte_msg)

    elif byte_command == CMD_PILE_CHARGING_STATUS:   # 充电状态上报
        pile_charging_status_handler(topic, byte_msg)

    elif byte_command == CMD_PILE_STOP_CHARGING:   # 充电桩停止充电上报
        pile_charging_stop_handler(topic, byte_msg)

    elif byte_command == CMD_PILE_REQUEST_PRICE:   # 充电桩请求电价信息
        pile_request_stage_tariff(topic, byte_msg)

    elif byte_command == CMD_PILE_UPLOAD_BILL:   # 上报离线充电帐单
        pile_upload_offline_bill(topic, byte_msg)

    elif byte_command == CMD_PILE_REQUEST_BALANCE:
        pile_request_user_balance(topic, byte_msg)

    elif byte_command == CMD_PILE_REQUEST_DEVICE_INFO:
        pile_request_device_info(topic, byte_msg)

    logging.info("*****************leave message_dispach****************")


# 0x0b
def pile_request_device_info(topic, byte_msg):
    """
    充电桩查询设备信息 说明：充电桩->服务器，48字节
    """
    logging.info("0x0a Enter pile_request_device_info function")

    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    # sn号
    device_sn = byte_msg[38:70].decode('utf-8').strip('\000')

    logging.info("充电桩Sn编码:{}, sn：{}".format(pile_sn, device_sn))

    # 回复电桩
    data = {
        "pile_sn": pile_sn,
        "device_sn": device_sn,
    }
    server_response_device_info(**data)
    logging.info("0x0a Leave pile_request_device_info function")


def server_response_device_info(*args, **kwargs):
    """0x8b
    服务器下发设备信 说明：服务器->充电桩，回复0b命令 （56字节）
    """
    logging.info("0x8a Enter server_response_device_info")
    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        logging.info("No Charging Pile SN")
        return

    b_pile_sn = get_32_byte(pile_sn)
    b_command = CMD_RESPONSE_DEVICE_INFO

    device_sn = kwargs.get("device_sn", "")
    b_device_sn = get_32_byte(device_sn)

    pile = ChargingPile.objects.select_related("station").filter(pile_sn=pile_sn).first()
    if pile is None:
        logging.info("No ChargingPile******************")
        return

    sub_time = pile.sub_time
    logging.info(sub_time)
    if sub_time:
        b_sub_date = get_byte_date(sub_time)
        logging.info("datetme:{}, {}".format(sub_time, b_sub_date))
    else:
        b_sub_date = bytes(4)

    pile_type = pile.pile_type_id
    b_pile_type = bytes([pile_type])

    gun_nums = pile.get_guns().count()
    b_gun_nums = bytes([gun_nums])

    seller_id = pile.station.seller_id
    b_seller_id = seller_id.to_bytes(4, byteorder="big")

    longitude = pile.station.longitude
    latitude = pile.station.latitude
    b_longitude = int(longitude * 1000000).to_bytes(4, byteorder="big")
    b_latitude = int(latitude * 1000000).to_bytes(4, byteorder="big")

    logging.info("{},{},{},{},{}, {}".format(b_pile_type, b_gun_nums, b_seller_id, b_longitude, b_latitude, b_sub_date))

    b_blank = bytes(5)

    b_data = b''.join([b_command, b_device_sn, b_sub_date, b_pile_type, b_gun_nums, b_seller_id, b_longitude, b_latitude, b_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    server_publish(pile_sn, b_reply_proto)

    logging.info("0x8a Leave server_response_device_info")


# 0x0a
def pile_request_user_balance(topic, byte_msg):
    """
    充电桩查询余额
    说明：充电桩->服务器，请求充电 （56字节）
    """
    logging.info("0x0a Enter pile_request_user_balance function")

    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)

    # 用户标识
    user_flag = byte_msg[38]
    cardnum_ordernum = byte_msg[39:73].decode('utf-8').strip('\000')
    password = byte_msg[73:91].decode('utf-8').strip('\000')

    logging.info("充电桩Sn编码:{}, 用户标识：{}， 用户名：{}， password:{}".format(pile_sn, user_flag, cardnum_ordernum, password))

    # 回复电桩
    data = {
        "pile_sn": pile_sn,
        "user_flag": user_flag,
        "cardnum_ordernum": cardnum_ordernum,
        "password": password,
    }
    server_response_user_balance(**data)
    logging.info("0x0a Leave pile_request_user_balance function")


# 0x8a
def server_response_user_balance(*args, **kwargs):
    """
    服务器回复查询余额
    说明：服务器->充电桩，回复0a命令 （56字节）
    """
    logging.info("0x8a Enter server_response_user_balance")
    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        logging.info("No Charging Pile SN")
        return

    user_flag = kwargs.get("user_flag", None)
    if user_flag is None:
        logging.info("user_flag does not exist")
        return

    cardnum_ordernum = kwargs.get("cardnum_ordernum", None)
    password = kwargs.get("password", None)

    balance = 0
    if user_flag == 1:      # 订单用户
        order = Order.objects.filter(out_trade_no=cardnum_ordernum).first()
        logging.info(order)
        if order:
            user = UserInfo.objects.filter(openid=order.openid).first()
            if user:
                balance = int((user.account_balance() - order.consum_money) * 100)
    elif user_flag == 2:       # 2RFID卡用户
        card = ChargingCard.objects.filter(card_num=cardnum_ordernum, cipher=password).first()
        logging.info(card)
        balance = int(card.money * 100)

    logging.info("balance:{}".format(balance))
    b_pile_sn = get_32_byte(pile_sn)
    b_command = CMD_RESPONSE_BALANCE
    b_user_flag = bytes([user_flag])
    b_cardnum_ordernum = get_32_byte(cardnum_ordernum, 34)
    b_balance = balance.to_bytes(4, byteorder='big')
    b_blank = bytes(8)

    b_data = b''.join([b_command, b_user_flag, b_cardnum_ordernum, b_balance, b_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    server_publish(pile_sn, b_reply_proto)

    logging.info("0x8a Leave server_response_user_balance")


# 0x09
def pile_upload_offline_bill(topic, byte_msg):
    """
    充电桩上报离线结束充电产生的帐单
    说明：充电桩->服务器，充电桩主动请求（88字节）
    """
    logging.info("0x09 Enter pile_upload_offline_bill function")

    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    # 枪口号
    gun_num = byte_msg[38]
    # 订单
    out_trade_no = byte_msg[39:71].decode('utf-8').strip('\000')
    logging.info("充电桩Sn编码:{}, 枪口：{}， 订单：{}".format(pile_sn, gun_num, out_trade_no))
    # 起始充电时间
    b_begin_time = byte_msg[71:78]
    begin_time = get_datetime_from_byte(b_begin_time)
    begin_readings = byte2integer(byte_msg, 78, 82)
    logging.info('起始充电时间: {}, 超始电量:{}'.format(begin_time, begin_readings))
    # 结束充电时间
    b_end_time = byte_msg[82:89]
    end_time = get_datetime_from_byte(b_end_time)
    end_readings = byte2integer(byte_msg, 89, 93)
    logging.info('结束充电时间: {}, 结束电量:{}'.format(end_time, end_readings))
    # 充电帐单金额
    money = byte2integer(byte_msg, 93, 97) * 0.01
    logging.info('充电帐单金额: {}.'.format(money))
    # 各个时间段电量
    b_interval_readings = byte_msg[97, 121]

    _readings = [b_interval_readings[i:i + 2] for i in range(0, len(b_interval_readings), 2)]

    # 回复电桩
    data = {
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "out_trade_no": out_trade_no,
    }
    server_reply_offline_bill(**data)

    logging.info("0x09 Leave pile_upload_offline_bill function")


# 0x89
def server_reply_offline_bill(*args, **kwargs):
    """
    服务器回复收到充电桩上报的帐单
    说明：服务器->充电桩，回复充电桩0x09命令（48字节）。
    """
    logging.info("0x08 Enter server_reply_offline_bill")
    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        logging.info("No Charging Pile SN")
        return

    gun_num = kwargs.get("gun_num", None)
    if gun_num is None:
        logging.info("gun num does not exist")
        return

    out_trade_no = kwargs.get("out_trade_no", None)
    if out_trade_no is None:
        logging.info("out_trade_no does not exist")
        return

    b_pile_sn = get_32_byte(pile_sn)
    b_command = CMD_REPLY_BILL
    b_gun_num = bytes([gun_num])
    b_out_trade_no = get_32_byte(out_trade_no)
    b_blank = bytes(14)

    b_data = b''.join([b_command, b_gun_num, b_out_trade_no, b_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    server_publish(pile_sn, b_reply_proto)

    logging.info("0x89 Leave server_reply_offline_bill")


# 0x08
def pile_request_stage_tariff(topic, byte_msg):
    """充电桩请求电价信息"""
    """说明：充电桩->服务器，充电桩主动请求（48字节）"""
    logging.info("0x08 Enter pile_request_stage_tariff")
    pile_sn = get_pile_sn(byte_msg)
    logging.info("充电桩Sn编码:{}".format(pile_sn))
    data = {
        "pile_sn": pile_sn
    }
    server_reply_stage_tafiff(**data)
    logging.info("0x08 Leave pile_request_stage_tariff")


# 0x88
def server_reply_stage_tafiff(*arg, **kwargs):
    """
    服务器下发阶段电价信息 说明：服务器->充电桩，回复充电桩0x08命令（64字节）。
    """
    logging.info("0x88 Enter server_reply_stage_tafiff")
    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        logging.info("No Charging Pile SN")
        return

    b_pile_sn = get_32_byte(pile_sn)
    b_command = CMD_REPLY_PRICE

    charg_pile = ChargingPile.objects.select_related("station").filter(pile_sn=pile_sn).first()

    interval_price_list = []
    service_price = 0       # 服务费
    is_seat_fee = 0         # 是否收占位费
    free_min = 0            # 免费时间
    occupy_fee = 0          # 每十分钟占位费
    if charg_pile:
        charg_price = charg_pile.station.chargingprice_set.filter(default_flag=1).first()
        charg_price_details = charg_price.prices.all()
        is_seat_fee = 0
        free_min = 0
        occupy_fee = 0
        for detail in charg_price_details:

            b_begin_hour = bytes([detail.begin_time.hour])
            b_begin_min = bytes([detail.begin_time.minute])
            b_end_hour = bytes([detail.end_time.hour])
            b_end_min = bytes([detail.end_time.minute])
            b_price = int(detail.price * 100).to_bytes(2, byteorder="big")
            if service_price == 0:
                service_price = int(detail.service_price * 100)

            interval_data = b''.join([b_begin_hour, b_begin_min, b_end_hour, b_end_min, b_price])
            interval_price_list.append(interval_data)
            if len(interval_price_list) == 8:
                break

        b_service_price = service_price.to_bytes(2, byteorder="big")
        logging.info("servcie price:{}".format(service_price))
    else:
        logging.info("Charging pile not exists")
        b_service_price = service_price.to_bytes(2, byteorder="big")

    data_counts = len(interval_price_list)
    b_data_counts = bytes([data_counts])

    b_interval_price_data = b''.join(interval_price_list)
    logging.info(b_interval_price_data)

    interval_blank = 48 - data_counts * 6
    b_interval_blank = bytes(interval_blank)

    b_is_seat_fee = bytes([is_seat_fee])
    b_free_min = bytes([free_min])
    b_occupy_fee = occupy_fee.to_bytes(2, byteorder="big")
    b_end_blank = bytes(8)
    b_data = b''.join([b_command, b_interval_price_data, b_interval_blank, b_service_price, b_data_counts,
                       b_is_seat_fee, b_free_min, b_occupy_fee, b_end_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    server_publish(pile_sn, b_reply_proto)

    logging.info("0x88 Leave server_reply_stage_tafiff")


# 83(0x83)
def pile_card_charging_request_hander(topic, byte_msg):
    """桩端向后台请求充电"""
    logging.info("0x83 Enter pile_card_charging_request_hander")
    pile_sn = get_pile_sn(byte_msg)
    logging.info("充电桩Sn编码:{}".format(pile_sn))

    card_type = byte_msg[38]
    logging.info('用户识别卡方式: {}'.format(card_type))
    # 保留四位
    gun_num = byte_msg[43]   # 枪口号
    logging.info("枪口号:{}".format(gun_num))

    oper_type = byte_msg[44]    # 操作类型(01:请求后台充电,02:请求后台停充)
    logging.info("操作类型：{}".format(oper_type))

    card_num = byte_msg[45:77].decode('utf-8').strip('\000')
    logging.info('卡号: {}'.format(card_num))

    password = byte_msg[77:93].decode('utf-8').strip('\000')
    logging.info("password:{}".format(password))
    if card_type != 1:  # IC卡
        logging.info("不是IC卡，类型错误。")
        return

    cur_time = datetime.datetime.now().date()
    # 判断卡号是否有效
    card = ChargingCard.objects.select_related("seller").filter(status=1, card_num=card_num, cipher=password).first()
    if not card:
        logging.info("此卡{}不存在或者处于禁用状态".format(card_num))
        return

    if card.seller and card.seller.status == 1:
        logging.info("此运营商已被停运")
        return

    pile = ChargingPile.objects.select_related("station").filter(pile_sn=pile_sn).first()
    # 判断电站是否支持刷卡
    if pile and pile.charg_mode == 1:
        logging.info("此充电桩不支持刷卡!")
        return

    if card.seller and card.seller_id != pile.station.seller_id:
        logging.info("此卡不属于此运营商,无法充电")
        return

    if card.station.count() > 0:
        if not card.station.filter(id=pile.station_id).exists():
            logging.info("此卡不属于该充电场,无法充电")
            return

    pile_gun = ChargingGun.objects.filter(charg_pile__pile_sn=pile_sn, gun_num=gun_num).first()
    if not pile_gun:
        logging.info("{}-{} 不存在".format(pile_sn, gun_num))
        return

    # 判断此卡是否有时间限制
    if card.is_valid_date == 1:
        if card.start_date is None or card.end_date is None:
            logging.warning("有效截止时间不能为空")
            return
        elif cur_time > card.end_date:
            logging.warning("此卡{}已经过期".format(card_num))
            return

    if card.pile_sn and card.gun_num:
        if card.pile_sn != pile_sn or card.gun_num != str(gun_num):
            logging.info("卡正在电桩SN{}枪口{}上充电".format(card.pile_sn, card.gun_num))
            return

    # 判断是否正在充电如果正在充电判断充电时间操作3s后，进行停充
    order = Order.objects.filter(charg_pile__pile_sn=pile_sn, gun_num=str(gun_num), openid=card.face_num, status__lt=2).first()
    if order and oper_type == 2:
        cur_dtime = datetime.datetime.now()
        diff_seconds = (cur_dtime - order.begin_time).seconds
        if diff_seconds > 3:
            stop_data = {
                "pile_sn": pile_sn,
                "gun_num": gun_num,
                "openid": order.openid,
                "out_trade_no": order.out_trade_no,
                "consum_money": int(order.consum_money.quantize(decimal.Decimal("0.01")) * 100),
                "total_reading": int(order.get_total_reading() * 100),
                "stop_code": 0,  # 0 主动停止，1被动响应
                "fault_code": 0,
                "start_model": order.start_model,
            }

            req_reply_cmd_data = {
                'out_trade_no': order.out_trade_no,
                'oper_name': '刷卡停充请求',
                'oper_user': '充电桩',
                'oper_time': datetime.datetime.now(),
                'comments': '充电桩向后台发送刷卡停充请求',
            }
            create_oper_log(**req_reply_cmd_data)

            server_send_stop_charging_cmd(**stop_data)

    if oper_type == 1 and card.money > settings.ACCOUNT_BALANCE:
        # 创建订单(充满为止), 发送充电命令
        openid = card.face_num
        out_trade_no = '{0}{1}{2}'.format(settings.OPERATORID, datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))

        start_model = 1  # 储值卡启动
        params = {
            "gun_num": gun_num,
            "openid": openid,
            "name": openid,
            "charg_mode": 0,    # 充满为止
            "out_trade_no": out_trade_no,
            "charg_pile": pile,
            "pile_name": pile.name,
            "seller_id": pile.station.seller_id,
            "seller_name": pile.station.seller.name,
            "station": pile.station,
            "station_name": pile.station.name,
            "start_model": start_model,   # 储值卡启动
            "balance": card.money,
        }
        order = Order.objects.create(**params)
        logging.info(order)
        out_trade_no = order.out_trade_no
        # 保存 订单
        pile_gun.out_trade_no = out_trade_no
        pile_gun.order_time = datetime.datetime.now()
        pile_gun.save(update_fields=["out_trade_no", "order_time"])

        data = {
            'pile_sn': pile_sn,
            'gun_num': int(order.gun_num),
            'out_trade_no': out_trade_no,
            'openid': order.openid,
            'charging_type': 0,  # 充电类型 1预约，0即时
            'subscribe_min': 0,
        }

        charg_policy = pile.charg_policy  # 充电策略是否使用(D0：1使用充电策略，0系统默认策略)(电站还是电桩为准)
        data["use_policy_flag"] = charg_policy
        # 1使用充电策略
        if charg_policy == 1:
            data["continue_charg_status"] = 0  # 断网可继续充电  1断网可继续充电，0不可以(那些用户？)
            data["occupy_status"] = pile.occupy_status  # 收取占位费 1收取占位费，0不收取
            data["subscribe_status"] = pile.subscribe_status  # 收取预约费
            data["low_fee_status"] = pile.low_offset  # 收取小电流补偿费
            data["low_restrict_status"] = pile.low_restrict  # 限制小电流输出

        data["start_model"] = start_model
        charging_policy_value = 0
        data["charging_policy_value"] = charging_policy_value
        data["balance"] = int(card.money * 100)
        logging.info(data)

        req_reply_cmd_data = {
            'out_trade_no': out_trade_no,
            'oper_name': '刷卡充电请求',
            'oper_user': '充电桩',
            'oper_time': datetime.datetime.now(),
            'comments': '充电桩向后台发送刷卡充电请求',
        }
        create_oper_log(**req_reply_cmd_data)

        server_send_charging_cmd(**data)

    logging.info("0x83 Leave pile_card_charging_request_hander")


# 1 (0x01)
def pile_status_handler_v12(topic, byte_msg):
    """
    接收充电桩状态上报，处理并回复版本信息给充电桩
    :param topic:
    :param byte_msg:
    :return:
    """
    logging.info("0x01 Enter pile_status_handler_v12 function")

    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    # 电桩类型
    pile_type = byte2integer(byte_msg, 38, 39)
    # 桩类型扩展
    ext_type = byte2integer(byte_msg, 39, 40)
    max_gun = ext_type & 0x0F       # 枪口数量D3-D0
    pile_mode = ext_type >> 7 & 0x01    # D7位
    # 桩属性
    pile_prop = byte_msg[40]
    logging.info('充电桩Sn编码:{},电桩类型: {},枪口数量:{}, 电桩类型模式:{}, 桩属性:{}'.format(pile_sn, pile_type, max_gun, pile_mode, pile_prop))

    ver_max = byte_msg[41]
    ver_mid = byte_msg[42]
    ver_min = byte_msg[43]
    logging.info('固件版本号:{}.{}.{}'.format(ver_max, ver_mid, ver_min))

    # 工作状态枪1 and 工作状态枪 2
    gun1_status = byte_msg[44]  # 00空闲，01：故障， 10充电，11充电结束未拔枪
    gun1_desc = byte_msg[45]
    logging.info('工作状态枪1:{}[{}]'.format(gun1_status, gun1_desc))
    # 枪1工作状态代码详细信息46 + 8

    gun2_status = byte_msg[54]
    gun2_desc = byte_msg[55]
    logging.info('工作状态枪2:{}[{}]'.format(gun2_status, gun2_desc))

    # 更新枪口状态
    gun1 = update_charging_gun_status(pile_sn, '0', gun1_desc, gun1_status)  # 枪1
    gun2 = update_charging_gun_status(pile_sn, '1', gun2_desc, gun2_status)  # 枪2

    # 通知前端
    send_data = {
        "return_code": "success",
        "cmd": "01",  # 电桩状态
    }
    # logging.info("{}----{}".format(gun1, gun2))
    if gun1:
        send_data["work_status"] = gun1.get_work_status_display()
        send_data["charg_status"] = gun1.charg_status.name
        logging.info(send_data)
        # 非空闲状态
        if gun1.work_status > 0 and gun1.charg_status_id > 0:
            send_data_to_client(pile_sn, gun1.gun_num, **send_data)

        if gun1.work_status == 1 and 6 > gun1.charg_status_id > 0:
            req_reply_cmd_data = {
                'out_trade_no': gun1.out_trade_no,
                'oper_name': '充电状态上报',
                'oper_user': '充电桩',
                'oper_time': datetime.datetime.now(),
                'comments': '充电桩上报状态,充电状态:【{}】{}'.format(gun1.charg_status_id, gun1.charg_status.name),
            }
            create_oper_log(**req_reply_cmd_data)

    if gun2:
        send_data["work_status"] = gun2.get_work_status_display()
        send_data["charg_status"] = gun2.charg_status.name
        logging.info(send_data)
        if gun2.work_status > 0 and gun1.charg_status_id > 0:
            send_data_to_client(pile_sn, gun2.gun_num, **send_data)

        if gun2.work_status == 1 and 6 > gun2.charg_status_id > 0:
            req_reply_cmd_data = {
                'out_trade_no': gun2.out_trade_no,
                'oper_name': '充电状态上报',
                'oper_user': '充电桩',
                'oper_time': datetime.datetime.now(),
                'comments': '充电桩上报状态,充电状态:【{}】{}'.format(gun2.charg_status_id, gun2.charg_status.name),
            }
            create_oper_log(**req_reply_cmd_data)
    # 2、回复版本信息to device
    try:
        charg_pile = ChargingPile.objects.get(pile_sn=pile_sn)
    except ChargingPile.DoesNotExist as ex:
        logging.warning("Illegal Pile:{}".format(ex))
        return
    # logging.info("{}----{}".format(gun1, gun2))
    pile_type = charg_pile.pile_type.id

    fireware = charg_pile.fireware
    if fireware is None:
        fireware = 0

    data = {
        "pile_sn": pile_sn,
        "dc_version": fireware if pile_type in [1, 2] else '0',      # 直流
        "ac_version": fireware if pile_type in [5, 6] else '0',      # 交流
        "power_distrib_version": fireware if pile_type in [4, 7] else '0',    # 电源分配主机
        "ac_dc_version": fireware if pile_type == 3 else '0'
    }
    logging.info(data)
    server_reply_version_info(**data)   # 回复版本信息

    logging.info("Leave pile_status_handler_v12 function")


def server_reply_version_info(*arg, **kwargs):
    """
    说明：服务器->充电桩，服务器收到充电桩状态上报（命令0x01）或电源功率分配主机状态上报（命令0x02）后，下发充电村桩版本信息（32字节）。
    """
    logging.info("Enter server_reply_version_info function")

    pile_sn = kwargs.get("pile_sn", None)
    if pile_sn is None:
        logging.warning(" Pile SN does not exist")
        return
    b_pile_sn = get_32_byte(pile_sn)

    b_command = CMD_PILE_VERSION_INFO
    b_current_time = get_byte_daytime(datetime.datetime.now())   # 哪个时间

    dc_ver = kwargs.get("dc_version", '0')
    dc_version = get_byte_version(dc_ver)

    ac_ver = kwargs.get("ac_version", '0')
    ac_version = get_byte_version(ac_ver)

    power_distrib_ver = kwargs.get("power_distrib_version", '0')
    power_distrib_version = get_byte_version(power_distrib_ver)

    ac_dc_ver = kwargs.get("ac_dc_version", '0')
    ac_dc_version = get_byte_version(ac_dc_ver)
    # logging.info("版本信息：{},{},{},{}".format(dc_version, ac_version, power_distrib_version, ac_dc_version))
    b_blank = bytes(12)
    b_data = b''.join([b_command, b_current_time, dc_version, ac_version, power_distrib_version, ac_dc_version, b_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    server_publish(pile_sn, b_reply_proto)

    logging.info("Leave server_reply_version_info function")


# 7 (0x84)--->0x04回复
def server_send_charging_cmd(*args, **kwargs):
    """
    服务器向充电桩下发充电指令 命令号0x84
    命令号0x84（1字节） + 枪口号（1字节）+ 充电类型（1字节）+ 充电策略（2字节）+ 充电策略值（4字节）+ 用户识别号（32字节）+ 订单号（32字节）
    + 同步时间（7字节） + 保留（8字节）
    此函数由用户扫描缴费调用，通过二维码的pile_sn 和 gun_num确定后台的数据内容
    :return:
    """
    logging.info("0x84 Enter server_send_charging_cmd function")
    logging.info(kwargs)
    pile_sn = kwargs.get("pile_sn", None)
    b_pile_sn = get_32_byte(pile_sn)

    b_command = CMD_SEND_CHARGING
    # 枪口号
    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])
    # 充电类型（来至前台） 根据前台用户信息判断 000充满为止，001按金额，010按分钟数，011按SOC 100按电量
    charg_type = kwargs.get("charging_type", 0)
    subscribe_min = kwargs.get("subscribe_min", 0)
    b_charging_type = bytes([charg_type << 7 | subscribe_min & 0x7f])

    # 充电策略 1、充电模式(后台or本地离线)
    start_model = kwargs.get("start_model", 0)  # D15-D14
    charging_way = kwargs.get("charging_way", 0)    # D13－D11
    # 充电策略是否使用(D0：1使用充电策略，0系统默认策略)
    continue_charg_status = kwargs.get("continue_charg_status", 0)  # 断网可继续充电
    occupy_fee_status = kwargs.get("occupy_status", 0)          # 收取占位费
    subscribe_fee_status = kwargs.get("subscribe_status", 0)    # 收取预约费
    low_fee_status = kwargs.get("low_fee_status", 0)            # 收取小电流补偿费
    low_restrict_status = kwargs.get("low_restrict_status", 0)  # 限制小电流输出
    use_policy_flag = kwargs.get("use_policy_flag", 0)

    charging_policy1 = start_model << 6 & 0xFF | charging_way << 3 & 0xFF | continue_charg_status << 2 & 0xFF \
                       | occupy_fee_status << 1 & 0xFf | subscribe_fee_status & 0xFF
    charging_policy2 = low_fee_status << 7 & 0xFF | low_restrict_status << 6 & 0xFF | use_policy_flag & 0xFf
    b_charging_policy1 = bytes([charging_policy1])
    b_charging_policy2 = bytes([charging_policy2])
    b_charging_policy = b''.join([b_charging_policy1, b_charging_policy2])
    # 充电策略值
    charging_policy_value = kwargs.get("charging_policy_value", 0)
    b_charging_policy_value = charging_policy_value.to_bytes(4, byteorder='big')

    out_trade_no = kwargs.get("out_trade_no", "")   # 订单号
    b_out_trade_no = get_32_byte(out_trade_no)

    b_send_time = get_byte_daytime(datetime.datetime.now())  # 同步时间

    balance = kwargs.get("balance", 0)      # 账号余额
    b_balance = balance.to_bytes(4, byteorder="big")
    b_blank = bytes(4)   # 保留4字节

    b_data = b''.join([b_command, b_gun_num, b_charging_type, b_charging_policy,
                     b_charging_policy_value, b_out_trade_no, b_send_time, b_balance, b_blank])

    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    logging.info(bytes.hex(b_reply_proto))
    server_publish(pile_sn, b_reply_proto)

    save_charging_cmd_to_db(pile_sn, gun_num, out_trade_no, bytes.hex(b_reply_proto), "start")
    # 更新用户使用电桩情况，用于杜绝一卡多充的情况
    openid = kwargs.get("openid", None)
    user_update_pile_gun(openid, start_model, pile_sn, gun_num)

    req_send_cmd_data = {
        'out_trade_no': out_trade_no,
        'oper_name': '发送启动命令.',
        'oper_user': '后台',
        'oper_time': datetime.datetime.now(),
        'comments': '后台向充电桩发送启动命令.',
    }
    create_oper_log(**req_send_cmd_data)

    logging.info("Leave server_send_charging_cmd function")


# 8 (0x04)
def pile_reply_charging_cmd_handler(topic, byte_msg):
    """
    说明：充电桩->服务器，此命令回复时间较长，服务器端超时判断为150S（80字节）。
    充电桩回复充电指令 命令号0x04
    :param byte_msg:
    :return:
    """
    logging.info("0x04 Enter pile_reply_charging_cmd_handler")
    if len(byte_msg) < 40:
        logging.warning("protocol data length is not enough")
        return
    data_nums = get_data_nums(byte_msg)
    logging.info(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    # 枪口号
    gun_num = byte_msg[38]
    logging.info("电桩编码SN:{}, 枪口:{}".format(pile_sn, gun_num))
    # 订单
    out_trade_no = byte_msg[39:71].decode('utf-8').strip('\000')
    logging.info("订单号:{}".format(out_trade_no))
    # 充电状态
    charg_status = byte_msg[71]
    logging.info("充电状态:{}".format(charg_status))
    begin_reading = byte2integer(byte_msg, 72, 76)
    # 保留（25字节）
    begin_reading = decimal.Decimal(begin_reading * settings.FACTOR_READINGS).quantize(decimal.Decimal("0.01"))
    data = {
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "out_trade_no": out_trade_no,
        "charg_status": 2,
        "begin_reading": begin_reading,
        "begin_time": datetime.datetime.now(),
        "status": 1,  # 未结帐
    }
    logging.info(data)
    # 清除发送充电命令超时判断
    ChargingCmdRecord.objects.filter(out_trade_no=out_trade_no, pile_sn=pile_sn, cmd_flag="start").delete()

    update_gun_order_status(**data)

    fault_code = get_fault_code(charg_status)
    status_name = fault_code.name if fault_code else "无"

    req_reply_cmd_data = {
        'out_trade_no': out_trade_no,
        'oper_name': '电桩回复充电命令',
        'oper_user': '充电桩',
        'oper_time': datetime.datetime.now(),
        'comments': '充电桩响应后台充电命令,充电状态:【{}】{},初始电表:{}'.format(charg_status, status_name, begin_reading),
    }
    create_oper_log(**req_reply_cmd_data)
    logging.info("Leave pile_reply_charging_cmd_handler")


def update_charging_gun_status(pile_sn, gun_num, charg_status=None, work_status=None):
    try:
        gun = ChargingGun.objects.get(charg_pile__pile_sn=pile_sn, gun_num=gun_num)

        if charg_status is not None:
            gun.charg_status_id = charg_status
        if work_status is not None:

            if gun.work_status != work_status and work_status in [0, 2, 9]:    # 非充电状态清除用户与电桩关联数据
                logging.info("清除用户电桩数据关联....{}-{}".format(gun.work_status, work_status))
                UserInfo.objects.filter(pile_sn=pile_sn, gun_num=gun_num).update(pile_sn=None, gun_num=None)
            gun.work_status = work_status

        logging.info("---------- end update_charging_gun_status ---------------")
        gun.save()
    except ChargingGun.DoesNotExist as ex:
        logging.warning(ex)
        gun = None
    except FaultCode.DoesNotExist as ex:
        logging.warning(ex)
        gun = None
    return gun


# 8---> 通知用户
def update_gun_order_status(**data):
    """
    pile_reply_charging_cmd_handler
    更新充电桩枪口的充电状态, 状态返回到用户界面，
    更新订单充电状态, 状态返回到用户界面，
    :param data: out_trade_no, gun_num , pile_sn, status
    :return:
    """
    pile_sn = data.get("pile_sn", None)
    gun_num = data.get("gun_num", 0)
    out_trade_no = data.get("out_trade_no", None)
    charg_status = data.get("charg_status", None)
    begin_reading = data.get("begin_reading", 0)
    begin_time = data.get("begin_time", None)
    status = data.get("status", 0)
    # 更新枪口的充电状态
    gun = update_charging_gun_status(pile_sn, gun_num, charg_status)
    # 更新订单状态和初始表值
    try:
        order = Order.objects.get(out_trade_no=out_trade_no)
        order.charg_status_id = charg_status
        order.begin_reading = begin_reading
        order.end_reading = begin_reading
        order.begin_time = begin_time
        order.status = status
        order.save()
        # 同步枪口订单时间
        gun.order_time = begin_time
        gun.save(update_fields=["order_time"])

        user = UserInfo.objects.filter(openid=order.openid).first()
        if user:
            if order.start_model == 0 and user.subscribe == 1:      # 启动方式：微信启动并且订阅的用户
                send_charging_start_message_to_user(order)  # 发送模板消息，通知客户充电开始

        send_data = {
            "return_code": "success",
            "cmd": "04",        # 充电命令
            "charg_status": order.charg_status.name,
            "begin_time": order.begin_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        logging.info(send_data)
        if order.start_charge_seq and len(order.start_charge_seq) > 0:
            ConnectorID = "{}{}".format(order.charg_pile.pile_sn, order.gun_num)
            Data = {
                "StartChargeSeq": order.start_charge_seq,
                "ConnectorID": ConnectorID,
            }
            if order.begin_time:
                Data["StartTime"] = order.begin_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                Data["StartTime"] = datetime.datetime.now().strptime("%Y-%m-%d %H:%M:%S")
            if charg_status:
                Data["StartChargeSeqStat"] = get_order_status(charg_status)
            else:
                Data["StartChargeSeqStat"] = get_order_status(gun.charg_status_id)

            logging.info(Data)
            notification_start_charge_result(**Data)    # 对接E充网

    except Order.DoesNotExist as ex:
        logging.warning(ex)
        send_data = {"return_code": "fail", "cmd": "04", "message": "订单不存在"}

    except FaultCode.DoesNotExist as ex:
        logging.warning(ex)
        send_data = {"return_code": "fail", "cmd": "04", "message": "状态码错误"}

    send_data_to_client(pile_sn, gun_num, **send_data)


# 9(0x05)----> 通知用户
def pile_report_car_info_handler(topic, byte_msg):
    """
    接收并处理充电桩上报的充电车辆信息
    9、开始充电作业
    说明：充电桩->服务器，充电桩上报车辆信息，该信息在上报充电指令之后上报（128字节）。
    :param topic:
    :param byte_msg:
    :return:
    """
    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    # 枪口号
    gun_num = byte_msg[38]
    # 订单
    logging.info(byte_msg)
    out_trade_no = byte_msg[39:71].decode('utf-8').strip('\000')
    # 充电国标协议 0交流单相，1交流三相，2普天协议，3国标2011，4国标2015
    protocol = byte_msg[71]
    logging.info("电桩编码:{},枪口号:{},订单:{},协议:{}".format(pile_sn, gun_num, out_trade_no, protocol))
    # 车辆VIN码
    vin_code = 0
    # if byte_msg[72] != b'\xff':
    #     vin_code = byte_msg[72:89].decode('utf-8').strip('\000')      # （备注：交流无此值）
    #     logging.info('VIN码:{}'.format(vin_code))
    logging.info("VIN码:{}".format(byte_msg[72:89].hex()))

    max_single_voltage = byte2integer(byte_msg, 89, 91)
    # 车辆最高充电电压
    max_voltage = byte2integer(byte_msg, 91, 93)
    # 车辆最高充电电流
    max_current = byte2integer(byte_msg, 93, 95)
    max_temp = byte_msg[95]

    begin_soc = byte_msg[96]
    logging.info('最高单体电池电压:{},最高充电电压:{},最高充电电流:{},最高充电温度:{},初始SOC:{}'.format(
        max_single_voltage, max_voltage, max_current, max_temp, begin_soc
    ))
    max_single_voltage = int(max_single_voltage * settings.FACTOR_CURRENT)
    max_voltage = int(max_voltage * settings.FACTOR_CURRENT)
    max_current = int(max_current * settings.FACTOR_CURRENT)
    max_temp = int(max_temp * settings.FACTOR_TEMPERATURE)
    begin_soc = begin_soc * settings.FACTOR_BATTERY_SOC

    # Save Data to Order in database
    save_data = {
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "out_trade_no": out_trade_no,
        "protocol": protocol,
        "vin_code": vin_code,
        "max_current": max_current,
        "max_voltage": max_voltage,
        "max_single_voltage": max_single_voltage,
        "max_temp":  max_temp,
        "begin_soc": begin_soc,
    }
    logging.info(save_data)
    update_order_car_info(**save_data)
    log_data = {
        'out_trade_no': out_trade_no,
        'oper_name': '电桩上传车辆信息',
        'oper_user': '充电桩',
        'oper_time': datetime.datetime.now(),
        'comments': '直流桩上传车辆信息，最高单体电池电压:{},最高充电电压:{},最高充电电流:{},最高充电温度:{},初始SOC:{}'.format(max_single_voltage, max_voltage, max_current, max_temp, begin_soc),
    }
    create_oper_log(**log_data)


def get_charging_price(station_id, curTime):
    """获取充电站的当前价格值"""
    try:
        chargingPrice = ChargingPrice.objects.filter(station__id=station_id, default_flag=1).first()
        if chargingPrice:
            priceDetail = chargingPrice.prices.filter(begin_time__lte=curTime, end_time__gte=curTime).first()
            if priceDetail:
                return priceDetail
            else:
                logging.warning("no price detail")
                return None
        else:
            return None
    except ChargingPrice.DoesNotExist as ex:
        logging.warning(ex)
        return None


# 9
def update_order_car_info(**data):
    """
    更新订单的车辆信息和协议，以及初始电表数、时间，SOC
    # 1、 保存相关车辆信息、协议、初始值到订单
    # 2、 充电明细表内追加一条初始充电信息记录
    :param data:
    :return:
    """
    out_trade_no = data.pop("out_trade_no", None)
    pile_sn = data.pop("pile_sn", None)
    gun_num = data.pop("gun_num", None)

    # 通知前端用户
    client_data = {
        "return_code": "success",
        "cmd": '05',
    }
    try:
        order = Order.objects.get(out_trade_no=out_trade_no)
        b_ret = stop_charging(order)
        if not b_ret:
            order.protocol = data["protocol"]
            order.vin_code = data["vin_code"]
            order.max_current = data["max_current"]
            order.max_voltage = data["max_voltage"]
            order.max_single_voltage = data["max_single_voltage"]
            order.max_temp = data["max_temp"]
            order.begin_soc = data["begin_soc"]
            order.save()

        client_data["charg_status"] = order.charg_status.name
        client_data["order_status"] = order.get_status_display()
        client_data["begin_soc"] = order.begin_soc
        logging.info(client_data)
    except Order.DoesNotExist as ex:
        client_data["return_code"] = "fail"
        client_data["errmsg"] = "订单不存在"
        logging.info(client_data)
    logging.info(client_data)
    send_data_to_client(pile_sn, gun_num, **client_data)


def stop_charging(order):
    if order.begin_time is None:
        stop_data = {
            "pile_sn": order.charg_pile.pile_sn,
            "gun_num": int(order.gun_num),
            "openid": order.openid,
            "out_trade_no": order.out_trade_no,
            "consum_money": 0,
            "total_reading": 0,
            "stop_code": 0,  # 0 主动停止，1被动响应，
            "fault_code": 92,  # 后台主动停止－通讯超时
            "start_model": order.start_model,
        }
        order.status = 2
        order.charg_status_id = 92
        order.save()
        logging.info(stop_data)
        server_send_stop_charging_cmd(**stop_data)
        return True
    else:
        return False


# 10 (0x85)
def server_reply_charging_info_handler(*args, **kwargs):
    """
    pile_charging_status_handler
    服务器->充电桩，服务器主动向充电桩发送帐单信息，收到06命令的回复（48字节）。
    2020-04- 17 增加余额数据
    """
    # logging.info(kwargs)
    pile_sn = kwargs.get("pile_sn")
    if pile_sn is None:
        logging.warning("电桩SN不能为空")
        return
    b_pile_sn = get_32_byte(pile_sn)

    out_trade_no = kwargs.get("out_trade_no", None)
    if out_trade_no is None:
        logging.warning("订单编号不能为空")
        return
    # 订单号
    b_out_trade_no = get_32_byte(out_trade_no)
    # 命令
    b_command = CMD_REPLY_CHARGING
    # 枪口号
    gun_num = kwargs.get("gun_num", 0)
    b_gun_num = bytes([gun_num])
    # 消费金额
    consum_money = kwargs.get("consum_money", None)
    b_consum_money = int(consum_money).to_bytes(4, byteorder="big")
    # 总的电表数
    total_reading = kwargs.get("total_reading", 0)
    b_total_reading = total_reading.to_bytes(4, byteorder="big")
    # 余额
    balance = kwargs.get("balance", 0)
    b_balance = balance.to_bytes(4, byteorder="big")
    # 保留
    b_blank = bytes(2)

    b_data = b''.join(
        [b_command, b_gun_num, b_out_trade_no, b_consum_money, b_total_reading, b_balance, b_blank])
    data_len = (len(b_data)).to_bytes(2, byteorder='big')
    # rand = bytes([random.randint(0, 2)])
    b_rand = bytes([0])
    byte_proto_data = b"".join([PROTOCAL_HEAD, b_pile_sn, b_rand, data_len, b_data])
    checksum = bytes([uchar_checksum(byte_proto_data)])
    byte_data = b"".join([b_pile_sn, b_rand, data_len, b_data, checksum])
    byte_data = message_escape(byte_data)
    b_reply_proto = b"".join([PROTOCAL_HEAD, byte_data, PROTOCAL_TAIL])
    server_publish(pile_sn, b_reply_proto)  # 发送主题


# 11(0x06)
def pile_charging_status_handler(topic, byte_msg):
    """
    11、充电状态上报 (服务端接收电桩上报的充电数据)
    说明：充电桩->服务器，上报充电过程数据，每3S左右更新一次，此命令无须服务器端回复（96字节）。
    数据区：命令号0x06（1字节）+ 枪口号（1字节）+ 用户识别号（32字节）+订单号（32字节）+时间（7字节）+所需电压值（2字节）+所需电流值（2字节）+输出电压值（2字节）
        +输出电流值（2字节）+当前电表读数（4字节）+保留（11字节）
    """
    logging.info("Enter pile_charging_status_handler")
    logging.info(byte_msg)
    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    # 枪口号
    gun_num = byte_msg[38]
    # 订单

    out_trade_no = byte_msg[39:71].decode('utf-8').strip('\000')
    logging.info('电桩编码Sn:{},枪口:{}, 订单:{}'.format(pile_sn, gun_num, out_trade_no))
    # 截止时间
    b_charg_time = byte_msg[71:78]
    charg_time = get_datetime_from_byte(b_charg_time)
    # 当前SOC
    current_soc = byte_msg[78]
    logging.info('充电时间:{},当前SOC:{}'.format(charg_time, current_soc))
    # # 所需电压值
    voltage = byte2integer(byte_msg, 79, 81)  # （备注：交流无此值）
    # 所需电流值
    current = byte2integer(byte_msg, 81, 83)  # （备注：交流无此值）
    # 输出电压值
    output_voltage = byte2integer(byte_msg, 83, 85)
    # 输出电流值
    output_current = byte2integer(byte_msg, 85, 87)
    # 枪头温度值
    gun_temp = byte_msg[87]
    gun_temp1 = byte_msg[88]
    # 柜内温度值
    cab_temp = byte_msg[89]
    cab_temp1 = byte_msg[90]
    # 当前电表读数
    current_readings = byte2integer(byte_msg, 91, 95)
    logging.info("所需电压值:{},所需电流值:{},输出电压值:{},输出电流值:{},枪头温度值:{}-{},柜内温度值:{}--{},当前电表读数{}"
                 .format(voltage, current, output_voltage, output_current, gun_temp, gun_temp1, cab_temp, cab_temp1, current_readings))

    charg_time = datetime.datetime.strptime(charg_time, '%Y-%m-%d %H:%M:%S')

    voltage = int(voltage * settings.FACTOR_VOLTAGE)
    current = int(current * settings.FACTOR_CURRENT)
    output_voltage = round(output_voltage * settings.FACTOR_VOLTAGE, 2)
    output_current = round(output_current * settings.FACTOR_CURRENT, 2)
    gun_temp = int(gun_temp * settings.FACTOR_TEMPERATURE)
    gun_temp1 = int(gun_temp1 * settings.FACTOR_TEMPERATURE)
    cab_temp = int(cab_temp * settings.FACTOR_TEMPERATURE)
    cab_temp1 = int(cab_temp1 * settings.FACTOR_TEMPERATURE)
    current_readings = current_readings * settings.FACTOR_READINGS

    prev_reading = 0
    curr_readings = decimal.Decimal(current_readings).quantize(decimal.Decimal("0.01"))
    try:
        order = Order.objects.get(out_trade_no=out_trade_no)
        stop_charging(order)
        prev_reading = order.prev_reading if order.prev_reading >= order.begin_reading else order.begin_reading
        order.prev_reading = curr_readings
        order.save(update_fields=['prev_reading'])
        # 记录充电过程
        if order.end_time is None:
            req_charging_data = {
                'out_trade_no': out_trade_no,
                'oper_name': '进入充电中',
                'oper_user': '充电桩',
                'oper_time': datetime.datetime.now(),
                'comments': '充电桩开始上传充电数据,所需电压值:{},所需电流值:{},输出电压值:{},输出电流值:{},枪头温度值:{}/{},柜内温度值:{}/{},当前电表读数{}'.format(voltage, current, output_voltage, output_current, gun_temp, gun_temp1, cab_temp, cab_temp1, curr_readings),
            }
            create_oper_log(**req_charging_data)
    except Order.DoesNotExist as ex:
        logging.warning("{}订单不存在".format(out_trade_no))

    serial_num = '{0}{1}'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(1000, 10000))

    data = {
        "serial_num": serial_num,
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "out_trade_no": out_trade_no,
        "end_time": datetime.datetime.now(),
        "end_reading": curr_readings,
        "current_soc": current_soc,
        "voltage": voltage,
        "current": current,
        "output_voltage": output_voltage,
        "output_current": output_current,
    }
    logging.info(data)

    org_data = {
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "out_trade_no": out_trade_no,
        "current_time": datetime.datetime.now(),
        "current_soc": current_soc,
        "voltage": voltage,
        "current": current,
        "output_voltage": output_voltage,
        "output_current": output_current,
        "gun_temp": gun_temp,
        "gun_temp1": gun_temp1,
        "cab_temp": cab_temp,
        "cab_temp1": cab_temp1,
        "current_reading": curr_readings,
        "prev_reading": prev_reading,
    }
    logging.info(org_data)
    OrderChargDetail.objects.create(**org_data)

    save_pile_charg_status_to_db(**data)

    charg_pile = ChargingPile.objects.filter(pile_sn=pile_sn).first()
    if charg_pile:
        current_time = datetime.datetime.now()
        defaults = {
            "recv_time": current_time,
        }
        if charg_pile.pile_type_id not in [5, 6]:
            defaults["over_time"] = current_time + datetime.timedelta(seconds=settings.CHARG_STATUS_OVER_TIME)
        else:
            defaults["over_time"] = current_time + datetime.timedelta(seconds=settings.CHARG_AC_STATUS_OVER_TIME)

        defaults["pile_type"] = charg_pile.pile_type_id
        ret = ChargingStatusRecord.objects.update_or_create(pile_sn=pile_sn, gun_num=gun_num, out_trade_no=out_trade_no,
                                                            defaults=defaults)
        logging.info(ret)

    else:
        logging.info("{}电桩不存在".format(pile_sn))

    logging.info("Leave pile_charging_status_handler")


# 11
def save_pile_charg_status_to_db(**data):
    """
    保存数据到 OrderRecord 表
    :param data: out_trade_no ,openid, order, charg_pile, end_time, end_reading
    :return:
    """
    out_trade_no = data.get("out_trade_no", None)   # 订单
    pile_sn = data.get("pile_sn", None)
    gun_num = data.get("gun_num", None)

    order = calculate_order(**data)
    if order is None:
        send_data = {"return_code": "fail", "cmd": "06", "message": "配置异常或订单不存在"}
        logging.info(send_data)
        send_data_to_client(pile_sn, gun_num, **send_data)
        return
    # 超过五分钟电表差值为零，电表故障
    if order.end_time and order.begin_time:
        total_mins = (order.end_time - order.begin_time).total_seconds() / 60
        if total_mins >= 5 and order.end_reading - order.begin_reading == 0:
            stop_error_data = {
                "pile_sn": data.get("pile_sn", None),
                "gun_num": data.get("gun_num", None),
                "openid": order.openid,
                "out_trade_no": out_trade_no,
                "consum_money": 0,
                "total_reading": 0,
                "stop_code": 0,  # 0 主动停止，1被动响应
                "fault_code": 33,  # 电表通讯故障
                "start_model": order.start_model,
            }
            logging.warning("电表通讯故障：{},{},{}".format(out_trade_no, order.end_reading - order.begin_reading, total_mins))
            server_send_stop_charging_cmd(**stop_error_data)
            return

    if order.end_reading - order.begin_reading < 0 or order.power_fee < 0 or order.service_fee < 0:
        stop_error_data = {
            "pile_sn": data.get("pile_sn", None),
            "gun_num": data.get("gun_num", None),
            "openid": order.openid,
            "out_trade_no": out_trade_no,
            "consum_money": 0,
            "total_reading": 0,
            "stop_code": 0,  # 0 主动停止，1被动响应
            "fault_code": 95,
            "start_model": order.start_model,
        }
        logging.warning("订单数据异常....订单：{},{},{},{}".format(out_trade_no, order.end_reading - order.begin_reading, order.power_fee, order.service_fee))
        server_send_stop_charging_cmd(**stop_error_data)
        return

    # 回复充电状态数据
    if order.start_model == 2:
        balance = 0
    else:
        balanc = order.get_balance()
        if balanc < 0:
            balanc = decimal.Decimal(0)
        balance = int(balanc.quantize(decimal.Decimal("0.01")) * 100)

    reply_charging_data = {
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "out_trade_no": out_trade_no,
        "consum_money": int(order.consum_money.quantize(decimal.Decimal("0.01")) * 100),
        "total_reading": int(order.get_total_reading() * 100),
        "balance": balance
    }
    logging.info(reply_charging_data)
    server_reply_charging_info_handler(**reply_charging_data)

    send_data = {
        "return_code": "success",
        "cmd": "06",            # 充电中状态上报
        "total_minutes": str(order.total_minutes()),
        "total_reading": str(order.get_total_reading()),
        "consum_money": str(order.consum_money.quantize(decimal.Decimal("0.01"))),
        "voltage": data.get("voltage", 0),
        "current": data.get("current", 0),
        "output_voltage": data.get("output_voltage"),
        "output_current": data.get("output_current"),
        "current_soc": data.get("current_soc", 0),
        "order_status": order.get_status_display(),
    }

    logging.info(send_data)
    send_data_to_client(pile_sn, gun_num, **send_data)

    # 判断是否终止充电操作
    stop_data = {
        "pile_sn": data.get("pile_sn", None),
        "gun_num": data.get("gun_num", None),
        "openid": order.openid,
        "out_trade_no": out_trade_no,
        "consum_money": int(order.consum_money.quantize(decimal.Decimal("0.01")) * 100),
        "total_reading": int(order.get_total_reading() * 100),
        "stop_code": 0,         # 0 主动停止，1被动响应，2消费清单已结束或不存在
        "start_model": order.start_model,
    }

    if order.openid == settings.ECHARGEUSER:    # E充网用户直接返回
        return

    if order.start_model == 1:  # 储蓄卡
        card = ChargingCard.objects.filter(card_num=order.openid).first()
        if card.money - order.consum_money <= 0.2:
            stop_data["fault_code"] = 93  # 后台主动停止－帐号无费用
            logging.info(stop_data)
            server_send_stop_charging_cmd(**stop_data)
    else:
        try:
            charg_user = UserInfo.objects.get(openid=order.openid)
            # 判断订单余额和账号余额是否同步,不同步更新订单余额
            sub_account = charg_user.is_sub_user()
            if sub_account:
                user_balance = sub_account.main_user.account_balance()
                if order.balance < user_balance:
                    order.balance = user_balance
                    order.save(update_fields=["balance"])
                if user_balance - order.consum_money <= 10:  # 附属用户
                    # 发送停充指令
                    stop_data["fault_code"] = 93  # 后台主动停止－帐号无费用
                    logging.info(stop_data)
                    server_send_stop_charging_cmd(**stop_data)
            else:
                user_balance = charg_user.account_balance()
                if order.balance < user_balance:
                    order.balance = user_balance
                    order.save(update_fields=["balance"])
                if user_balance - order.consum_money <= 0.2:
                    # 发送停充指令
                    stop_data["fault_code"] = 93    # 后台主动停止－帐号无费用
                    logging.info(stop_data)
                    server_send_stop_charging_cmd(**stop_data)
        except UserInfo.DoesNotExist as ex:
            logging.warning(ex)
            # 发送停充指令
            stop_data["fault_code"] = 93        # 后台主动停止－用户停止
            logging.info(stop_data)
            server_send_stop_charging_cmd(**stop_data)

        if order.charg_mode == 1:     # (1, '按金额') 将剩余的钱转到用户帐上
            if order.total_fee - order.consum_money <= 0:
                stop_data["fault_code"] = 94  # 后台主动停止－设定条件满足
                logging.info(stop_data)
                server_send_stop_charging_cmd(**stop_data)
        elif order.charg_mode == 2:     # (2, '按分钟数')
            delta_time = (order.end_time - order.begin_time).seconds / 60
            if delta_time >= order.charg_min_val:
                stop_data["fault_code"] = 94  # 后台主动停止－设定条件满足
                logging.info(stop_data)
                server_send_stop_charging_cmd(**stop_data)
        elif order.charg_mode == 3:     # (3, '按SOC')
            if order.end_soc >= order.charg_soc_val:
                stop_data["fault_code"] = 94  # 后台主动停止－设定条件满足
                logging.info(stop_data)
                server_send_stop_charging_cmd(**stop_data)
        elif order.charg_mode == 4:     # (4, '按电量')
            if order.end_reading - order.end_reading >= order.charg_reading_val:
                stop_data["fault_code"] = 94  # 后台主动停止－设定条件满足
                logging.info(stop_data)
                server_send_stop_charging_cmd(**stop_data)


def calculate_order(**kwargs):
    out_trade_no = kwargs.get("out_trade_no", None)   # 订单
    pile_sn = kwargs.get("pile_sn", None)
    gun_num = kwargs.get("gun_num", None)
    end_time = kwargs.get("end_time", datetime.datetime.now())
    output_voltage = kwargs.get("output_voltage", 0)
    output_current = kwargs.get("output_current", 0)
    charg_status = kwargs.pop("charg_status", None)
    order_status = kwargs.pop("status", None)       # 前端主动停止
    end_reading = kwargs.get("end_reading", 0)

    # logging.info(kwargs)
    try:
        gun = ChargingGun.objects.get(charg_pile__pile_sn=pile_sn, gun_num=gun_num)
    except ChargingGun.DoesNotExist as ex:
        logging.warning(ex)
        return None

    try:
        order = Order.objects.get(out_trade_no=out_trade_no)
    except Order.DoesNotExist as ex:
        logging.warning(ex)
        return None
    # 获取当前价格
    charg_pile = gun.charg_pile
    if charg_pile.station is None:
        logging.warning("{}:电桩或电站的价格策略没有设置".format(charg_pile.station.name))
        return order

    price = get_charging_price(charg_pile.station.id, end_time)
    if price is None:
        logging.warning("{}充电桩价格不能为空.".format(charg_pile.station))
        return order

    try:
        currRec = OrderRecord.objects.get(out_trade_no=out_trade_no, price_begin_time=price.begin_time, price_end_time=price.end_time)
        currRec.end_time = kwargs["end_time"]
        if end_reading > currRec.end_reading:
            currRec.end_reading = end_reading
        currRec.current_soc = kwargs["current_soc"]
        currRec.accumulated_readings = currRec.end_reading - currRec.begin_reading
        if currRec.accumulated_readings <= 0:
            currRec.accumulated_readings = 0
        currRec.accumulated_amount = currRec.accumulated_readings * currRec.price
        currRec.accumulated_service_amount = currRec.accumulated_readings * currRec.service_price
        if currRec.station_id is None:
            currRec.station_id = charg_pile.station_id

        if currRec.seller_id is None:
            currRec.seller_id = charg_pile.station.seller_id

        currRec.save()
    except OrderRecord.DoesNotExist as ex:
        logging.info("the first record:{}".format(ex))
        first_data = dict()
        first_data["order"] = order
        first_data["station_id"] = charg_pile.station_id
        first_data["seller_id"] = charg_pile.station.seller_id
        first_data["serial_num"] = kwargs["serial_num"]
        first_data["pile_sn"] = pile_sn
        first_data["gun_num"] = gun_num
        first_data["out_trade_no"] = out_trade_no
        first_data["price"] = price.price
        first_data["service_price"] = price.service_price
        if order.begin_time is None:
            logging.warning("订单开始时间为空。")
            order.begin_time = kwargs["end_time"]
            order.begin_reading = kwargs["end_reading"]
            first_data["begin_time"] = kwargs["end_time"]
            first_data["begin_reading"] = end_reading
        else:
            first_data["begin_time"] = order.begin_time
            if order.end_reading >= order.begin_reading:
                first_data["begin_reading"] = order.end_reading
            else:
                first_data["begin_reading"] = order.begin_reading

        first_data["end_time"] = kwargs["end_time"]
        first_data["price_begin_time"] = price.begin_time
        first_data["price_end_time"] = price.end_time
        first_data["current_soc"] = kwargs["current_soc"]
        first_data["end_reading"] = end_reading
        first_data["accumulated_readings"] = first_data["end_reading"] - first_data["begin_reading"]
        if first_data["accumulated_readings"] <= 0:
            first_data["accumulated_readings"] = 0
        first_data["accumulated_amount"] = first_data["accumulated_readings"] * price.price
        first_data["accumulated_service_amount"] = first_data["accumulated_readings"] * price.service_price
        logging.info(first_data)
        currRec = OrderRecord.objects.create(**first_data)

    totals = OrderRecord.objects.filter(out_trade_no=out_trade_no)\
        .aggregate(
            accumulated_amount=Sum("accumulated_amount", output_field=DecimalField(decimal_places=2)),
            accumulated_service_amount=Sum('accumulated_service_amount', output_field=DecimalField(decimal_places=2))
            )

    accumulated_amount = totals.get('accumulated_amount') if totals.get('accumulated_amount') is not None else decimal.Decimal(0)
    accumulated_service_amount = totals.get('accumulated_service_amount') if totals.get('accumulated_service_amount') is not None else decimal.Decimal(0)

    order.end_time = currRec.end_time
    order.end_reading = currRec.end_reading
    order.total_readings = order.end_reading - order.begin_reading
    if order.total_readings < 0:
        order.total_readings = 0
    order.power_fee = accumulated_amount
    order.service_fee = accumulated_service_amount
    # order.park_fee = (order.total_hours() * price.charg_price.parking_fee).quantize(decimal.Decimal("0.01"))
    order.consum_money = order.power_fee + order.service_fee
    order.end_soc = currRec.current_soc
    order.charg_status = charg_status if charg_status is not None else gun.charg_status
    order.output_voltage = output_voltage
    order.output_current = output_current
    if order_status:
        order.status = order_status
    order.save(update_fields=['end_time', 'prev_reading', 'end_reading',
                              'total_readings', 'power_fee', 'service_fee',
                              'consum_money', 'end_soc', 'charg_status', 'status', 'output_voltage', 'output_current'])
    return order


# 12 (0x86)
def server_send_stop_charging_cmd(*args, **kwargs):
    """
    12、服务器主动下发停止充电或停止充电确认
     说明：说明：服务器->充电桩，服务器主动向充电桩发送停止充电指令（80字节）。
     数据区：命令号0x86（1字节）+枪口号（1字节）+用户识别号（32字节）+订单号（32字节）+ 消费金额(4字节) +保留（1字节）
    """
    logging.info("Enter server_send_stop_charging_cmd function")

    pile_sn = kwargs.get("pile_sn")
    if pile_sn is None:
        logging.warning("pile_sn can not be empty")
        return
    b_pile_sn = get_32_byte(pile_sn)

    out_trade_no = kwargs.get("out_trade_no", None)
    if out_trade_no is None:
        logging.warning("Order Can not Be Empty")
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
            consum_money = order.consum_money * 100 if order is not None else 0
        except Order.DoesNotExist as ex:
            logging.warning(ex)
            return

    b_consum_money = int(consum_money).to_bytes(4, byteorder="big")
    # 总的电表数
    total_reading = kwargs.get("total_reading", 0)
    b_total_reading = total_reading.to_bytes(4, byteorder="big")
    # 停止标记
    stop_code = kwargs.get("stop_code", 0)
    b_stop_code = bytes([stop_code])
    # 运行状态标记
    state_code = kwargs.get("state_code", 3)
    b_state_code = bytes([state_code])
    # 故障代码
    fault_code = kwargs.get("fault_code", 0)
    b_fault_code = bytes([fault_code])
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
    # 保存停止充电指令
    if stop_code == 0:
        save_charging_cmd_to_db(pile_sn, gun_num, out_trade_no, bytes.hex(b_reply_proto), "stop")
        fault = get_fault_code(fault_code)
        status_name = fault.name if fault else '无'

        req_send_cmd_data = {
            'out_trade_no': out_trade_no,
            'oper_name': '发送停止充电命令。',
            'oper_user': '后台',
            'oper_time': datetime.datetime.now(),
            'comments': '后台向充电桩发送停充命令.故障代码:[{}]{},运行状态:{}'.format(fault_code, status_name, state_code),
        }
        create_oper_log(**req_send_cmd_data)

    openid = kwargs.get("openid", None)
    start_model = kwargs.get("start_model", None)
    user_update_pile_gun(openid, start_model, None, None)

    logging.info("Leave server_send_stop_charging_cmd function")


# 13 (0x07)
def pile_charging_stop_handler(topic, byte_msg):
    """
    13、充电桩停止充电回复或主动上报
    说明：充电桩->服务器，充电桩主动上报停止充电或回复0x86命令（80字节）。
    :param topic:
    :param byte_msg:
    :return:
    """
    logging.info("0x07 Enter pile_charging_stop_handler function")
    data_nums = get_data_nums(byte_msg)
    # 读取电桩编码(sn)
    pile_sn = get_pile_sn(byte_msg)
    # 枪口号
    gun_num = byte2integer(byte_msg, 38, 39)
    # 订单
    out_trade_no = byte_msg[39:71].decode('utf-8').strip('\000')
    logging.info("电桩编码:{},枪口:{},订单:{}".format(pile_sn, gun_num, out_trade_no))
    # 当前SOC
    current_soc = byte_msg[71]
    # 当前电表读数
    current_reading = int.from_bytes(byte_msg[72:76], byteorder="big")
    # 停止充电回复代码 0、已充满，1后台中止，2车端停止，3故障停止 4、已中止的帐单或充电机处于空闲
    stop_code = byte_msg[76]
    # 运行状态码
    state_code = byte_msg[77]
    # 故障代码
    fault_code = byte_msg[78]
    logging.info("当前SOC:{},当前电表读数:{},停止充电回复代码:{},状态码:{}, 故障代码:{}".format(current_soc, current_reading, stop_code, state_code, fault_code))
    # 保留（7字节）
    faultCode = get_fault_code(fault_code)
    status_name = faultCode.name if FaultCode else '无'
    serial_num = '{0}{1}'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(1000, 10000))

    data = {
        "serial_num": serial_num,
        "pile_sn": pile_sn,
        "gun_num": gun_num,
        "out_trade_no": out_trade_no,
        "end_time": datetime.datetime.now(),
        "end_reading": decimal.Decimal(current_reading * settings.FACTOR_READINGS),
        "current_soc": current_soc,
        "charg_status": faultCode,
        "status": 2,        # 订单结账
    }
    logging.info(data)
    # 清除充电状态记录
    ret = ChargingStatusRecord.objects.filter(pile_sn=pile_sn, gun_num=gun_num, out_trade_no=out_trade_no).delete()
    logging.info('清除充电状态:{}'.format(ret))
    # 删除停止指令
    ret = ChargingCmdRecord.objects.filter(out_trade_no=out_trade_no, pile_sn=pile_sn, cmd_flag="stop").delete()
    logging.info('删除停止指令:{}'.format(ret))
    # 订单计算(前端主动停止)
    if stop_code == 0:
        order = calculate_order(**data)
        req_send_cmd_data = {
            'out_trade_no': out_trade_no,
            'oper_name': '充电桩发送停止充电命令',
            'oper_user': '充电桩',
            'oper_time': datetime.datetime.now(),
            'comments': '充电桩向后台发送停充命令, 故障代码:[{}]{}, 运行状态码:{}'.format(fault_code, status_name, state_code),
        }
        create_oper_log(**req_send_cmd_data)
    else:
        try:
            order = Order.objects.get(out_trade_no=out_trade_no, status__lt=2)
            order.charg_status = faultCode
            order.status = 2  # 结账
            order.save(update_fields=['charg_status', 'status'])
            logging.info("更新订单状态")
        except Order.DoesNotExist as ex:
            logging.warning("{}:{}订单不存在".format("pile_charging_stop_handler", out_trade_no))
            return

    # 用户账号扣款
    if order:
        user_account_deduct_money(order)
    else:
        logging.info("订单不存在")

    # stop_code = 0 桩端主动停止
    if stop_code == 0:
        stop_data = {
            "pile_sn": pile_sn,
            "gun_num": gun_num,
            "openid": order.openid,
            "out_trade_no": out_trade_no,
            "consum_money": order.consum_money * 100,
            "total_reading": int(order.get_total_reading() * 100),
            "stop_code": 1,         # 0 主动停止，1被动响应，2消费清单已结束或不存在
            "state_code": state_code,
            "fault_code": 0,
            "start_model": order.start_model,
        }
        logging.info(stop_data)
        server_send_stop_charging_cmd(**stop_data)  # 回复电桩
    # 判断是否为E充网充电
    if order.start_charge_seq and len(order.start_charge_seq) > 0:
        # 推送停止充电结果
        Data = {
            "StartChargeSeq": order.start_charge_seq,
            "ConnectorID": "{}{}".format(pile_sn, gun_num),
        }
        if order.charg_status:
            Data["StartChargeSeqStat"] = 4
        else:
            Data["StartChargeSeqStat"] = 5

        Data["SuccStat"] = 0
        Data["FailReason"] = 0

        notification_stop_charge_result(**Data)

    # 通知前端
    if order:
        send_data = {
            "return_code": "success",
            "cmd": "07",            # 充电状态上报
            "total_minutes": str(order.total_minutes()),
            "total_reading": str(order.get_total_reading()),
            "consum_money": str(order.consum_money.quantize(decimal.Decimal("0.01"))),
            "charg_status": order.charg_status.name,
            "order_status": order.get_status_display(),
        }
    else:
        send_data = {"return_code": "fail", "cmd": "07", "message": "订单不存在"}
    logging.info(send_data)
    send_data_to_client(pile_sn, gun_num, **send_data)

    logging.info("Leave pile_charging_stop_handler function")


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
    logging.info("Enter is_legal_message function")

    byte_data = byte_msg
    head_flag = bytes.hex(byte_data[0:2])
    tail_flag = bytes.hex(byte_data[-2:])
    # logging.info("header:{}----tail:{}".format(head_flag, tail_flag))

    if head_flag.upper() == 'AAAA' and tail_flag == "5555":
        # 去除转义符
        byte_data = byte_data.replace(b'\xaa\x7e', b'\xaa')
        byte_data = byte_data.replace(b'\x55\x7e', b'\x55')
        byte_data = byte_data.replace(b'\x7e\x7e', b'\x7e')
        # 校验数据
        remote_check_sum = int(bytes.hex(byte_data[-3:-2]), 16)
        local_check_sum = uchar_checksum(byte_data[0:-3])
        if remote_check_sum == local_check_sum:  #数据校验
            return byte_data
        else:
            logging.warning("数据校验和失败......")
            return None
    else:
        logging.warning("非法协议......")
        return None


def on_subscribe(client, userdata, mid, granted_qos):
    """
    判断订阅成功和失败
    """
    logging.info("on subscribe callback result:{}".format(mid))
    if len(client.topic_ack) == 0:
        return

    for index, t in enumerate(client.topic_ack):
        if t[1] == mid:
            client.topic_ack.pop(index)


# 链接 redis
def connect_redis():
    pool = redis.ConnectionPool(host=settings.MQTT_REDIS_URL, port=settings.MQTT_REDIS_PORT, db=2)
    try:
        redis_client = redis.Redis(connection_pool=pool)
    except Exception as err:
        logging.warning(err)
        raise err

    return redis_client


if __name__ == "__main__":
    port = 1883
    # 初始化客户端
    mqtt.Client.connected_flag = False
    mqtt.Client.bad_connection_flag = False
    mqtt.Client.topic_ack = []

    # 连接到mqtt broker
    logging.info("Connecting to broker:{}".format(settings.MQTT_HOST))
    try:
        client = mqtt.Client(client_id=DEVICENAME, clean_session=True)
        client.username_pw_set(settings.USERNAME, settings.PASSWORD)
        # 指定事件回调函数
        client.on_message = on_message
        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_disconnect = on_disconnect
        client.on_log = on_log
        ret = client.connect(settings.MQTT_HOST, port, 60)
    except Exception as ex:
        logging.warning("connect to mqtt server fail:{}".format(ex))
        sys.exit(1)

    loop_flag = True
    r = connect_redis()
    # executor = ThreadPoolExecutor(5)
    # loop = asyncio.get_event_loop()
    # asyncio.ensure_future(loop.run_in_executor(executor, charg_reply_to_work_overtime))

    # Continue monitoring the incoming messages for subscribed topic
    def Quit(signum, frame):
        client.disconnect()
        client.loop_stop()
        global loop_flag
        loop_flag = False
        # executor.shutdown()
        # loop.close()
        logging.info("程序退出。。。")
        sys.exit()

    signal.signal(signal.SIGINT, Quit)
    signal.signal(signal.SIGTERM, Quit)

    client.loop_forever()
