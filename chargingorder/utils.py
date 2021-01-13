# coding=utf-8
import binascii
import datetime
import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from cards.models import ChargingCard
from chargingorder.models import ChargingCmdRecord, GroupName, Track
from chargingstation import settings
from django.db.models import F
from wxchat.models import UserInfo, UserAcountHistory, SubAccountConsume, GiftMoneyRecord, GiftConsumeRecord
from wxchat.utils import send_charging_end_message_to_user

channel_layer = get_channel_layer()


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
    byte_list = []
    for v in ver_list:
        byte_list.append(bytes([int(v)]))

    return b''.join(byte_list)


def get_byte_daytime(dtime=datetime.datetime.now()):
    """
    返回七字节的时间
    :param dtime:
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


def get_datetime_from_byte(byte_msg):
    high_year = byte_msg[0]
    low_year = byte_msg[1]
    month = byte_msg[2]
    day = byte_msg[3]
    hour = byte_msg[4]
    minute = byte_msg[5]
    second = byte_msg[6]
    date_time = '{0}{1}-{2}-{3} {4}:{5}:{6}'.format(high_year, low_year, month, day, hour, minute, second)
    return date_time


def get_byte_date(dt):
    """
    返回四字节的时间
    :param dt:
    :return:
    """
    high_year, low_year = divmod(dt.year, 100)
    b_high_year = bytes([high_year])
    b_low_year = bytes([low_year])
    b_month = bytes([dt.month])
    b_day = bytes([dt.day])
    ret_value = b''.join([b_high_year, b_low_year, b_month, b_day])
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
        # checksum += data[i]
        checksum &= 0xFF  # 强制截断

    return checksum


def message_escape(byte_msg):
    """增加转义字符"""
    byte_data = byte_msg
    byte_data = byte_data.replace(b'\x7e', b'\x7e\x7e')
    byte_data = byte_data.replace(b'\xaa', b'\xaa\x7e')
    byte_data = byte_data.replace(b'\x55', b'\x55\x7e')

    return byte_data


def message_unescape(byte_msg):
    """取消字符转义"""
    byte_data = byte_msg
    byte_data = byte_data.replace(b'\xaa\x7e', b'\xaa')
    byte_data = byte_data.replace(b'\x55\x7e', b'\x55')
    byte_data = byte_data.replace(b'\x7e\x7e', b'\x7e')
    return byte_data


def save_charging_cmd_to_db(pile_sn, gun_num, out_trade_no, send_cmd, flag):
        charging_cmd_data = {
            "send_cmd": send_cmd,
            "send_count": 1,
            "send_time": datetime.datetime.now(),
            "over_time": datetime.datetime.now() + datetime.timedelta(seconds=settings.CHARGING_SEND_CMD_INTERVAL),
            "cmd_flag": flag,
        }
        logging.info(charging_cmd_data)
        ret = ChargingCmdRecord.objects.update_or_create(out_trade_no=out_trade_no, pile_sn=pile_sn, gun_num=gun_num, defaults=charging_cmd_data)
        logging.info(ret)


def send_data_to_client(pile_sn, gun_num, **data):
    group_name = 'group_{}_{}'.format(pile_sn, gun_num)
    async_to_sync(channel_layer.group_send)(group_name, {"type": "chat.message", "message": json.dumps(data)})
    # try:
    #     group = GroupName.objects.get(name=group_name)
    #     async_to_sync(channel_layer.group_send)(group.name, {"type": "chat.message", "message": json.dumps(data)})
    # except GroupName.DoesNotExist as ex:
    #     print(ex)


def user_account_deduct_money(order):
    """扣款"""
    logging.info("---------------Enter user_account_deduct_money--------------------")
    if order.begin_time is None:        # 充电命令未得到回复
        return
    logging.info("状态：{}，支付时间：{}, 实付金额：{}".format(order.status, order.pay_time, order.cash_fee))
    if order.status == 2 and order.pay_time is None and order.cash_fee == 0:
        consum_money = order.consum_money
        openid = order.openid
        logging.info("启动方式：{},{}".format(order.start_model, consum_money))
        log_data = {
            'out_trade_no': order.out_trade_no,
            'oper_name': '',
            'oper_user': '后台',
            'oper_time': datetime.datetime.now(),
            'comments': '',
        }

        if order.start_model == 1:      # 储值卡启动
            try:
                card = ChargingCard.objects.get(face_num=openid)
                card.money = card.money - consum_money
                card.save(update_fields=['money'])
                logging.info("card.money：{}".format(card.money))
                order.pay_time = datetime.datetime.now()
                order.cash_fee = consum_money
                order.balance = card.money
                order.save(update_fields=['pay_time', 'cash_fee', 'balance'])
                log_data["oper_name"] = "储值卡结算"
                log_data["comments"] = "订单金额:{},账户余额:{}".format(consum_money, card.money)
            except ChargingCard.DoesNotExist as ex:
                logging.info(ex)
                log_data["oper_name"] = "储值卡结算失败"
                log_data["comments"] = "储值卡不存在"
        else:
            try:
                user = UserInfo.objects.get(openid=openid)
                sub_account = None
                if order.main_openid:
                    sub_account = user
                    user = UserInfo.objects.get(openid=order.main_openid)

                subscribe = user.subscribe

                if sub_account:  # 附属账户
                    order_data = {
                        "account": sub_account,
                        "out_trade_no": order.out_trade_no,
                        "charg_pile": order.charg_pile,
                        "gun_num": order.gun_num,
                        "consum_money": order.consum_money,
                    }
                    logging.info(order_data)
                    SubAccountConsume.objects.create(**order_data)

                    account_balance_calc(user, consum_money, order.out_trade_no)
                else:
                    his_data = {
                        "name": user.name if user.name is not None else user.nickname,
                        "openid": user.openid,
                        "total_money": user.total_money,
                        "consume_money": user.consume_money,
                        "binding_amount": user.binding_amount,
                        "consume_amount": user.consume_amount
                    }
                    UserAcountHistory.objects.create(**his_data)
                    # 扣款(余额扣款，不足则扣赠送金额)
                    # UserInfo.objects.filter(openid=openid).update(consume_money=F('consume_money') + consum_money)
                    account_balance_calc(user, consum_money, order.out_trade_no)
                    log_data["oper_name"] = "微信结算"
                    log_data["comments"] = "订单金额:{},账户余额:{}".format(consum_money, user.account_balance())

                order.pay_time = datetime.datetime.now()
                order.cash_fee = consum_money
                order.balance = user.account_balance()
                order.save(update_fields=['pay_time', 'cash_fee', 'balance'])
                if order.start_model == 0 and subscribe == 1:
                    send_charging_end_message_to_user(order)
            except UserInfo.DoesNotExist as ex:
                logging.warning(ex)
                log_data["oper_name"] = "微信结算失败"
                log_data["comments"] = "用户不存在"

            create_oper_log(**log_data)
    logging.info("---------------Leave user_account_deduct_money--------------------")


def account_balance_calc(user, consum_money, out_trade_no):
    if user.recharge_balance() >= consum_money:
        user.consume_money += consum_money
        user.save(update_fields=["consume_money"])
        # UserInfo.objects.filter(openid=openid).update(consume_money=F('consume_money') + consum_money)
    else:
        if user.recharge_balance() < 0:
            diff_val = consum_money
        else:
            diff_val = consum_money - user.recharge_balance()

        user.consume_money += user.recharge_balance() if user.recharge_balance() > 0 else 0  # 扣除充值金额
        user.consume_amount += diff_val  # 扣除赠送金额
        user.save(update_fields=["consume_money", "consume_amount"])

        recs = {
            "out_trade_no": out_trade_no,
            "name": user.name if user.name else user.nickname,
            "openid": user.openid,
            "consume_amount": diff_val,
        }
        logging.info(recs)
        GiftConsumeRecord.objects.create(**recs)
        # recs = GiftMoneyRecord.objects.filter(openid=user.openid, status=True)
        # for r in recs:
        #     rm = r.remain_money()
        #     if rm > diff_val:
        #         r.consume_amount += diff_val
        #         r.save(update_fields=["consume_amount"])
        #         break
        #     else:
        #         r.consume_amount += rm
        #         diff_val -= rm
        #         r.status = False
        #         r.save(update_fields=["consume_amount", "status"])


def user_update_pile_gun(openid, start_model, pile_sn, gun_num):
    """更新用户当前使用的电桩sn和枪口号"""
    logging.info("openid:{}, start_model:{}, pile_sn:{}, gun_num:{}".format(openid, start_model, pile_sn, gun_num))
    if start_model == 0:
        UserInfo.objects.filter(openid=openid).update(pile_sn=pile_sn, gun_num=gun_num)
    elif start_model == 1:
        ChargingCard.objects.filter(card_num=openid).update(pile_sn=pile_sn, gun_num=gun_num)


def create_oper_log(**kwargs):
    logging.info(kwargs)
    Track.objects.create(**kwargs)