# -*-coding:utf-8-*-
import datetime

from django.urls import reverse

from chargingstation import settings
from wxchat.models import UserInfo
from wxchat.views import wxClient


def get_user_balance(openid):
    try:
        user = UserInfo.objects.get(openid=openid)
        sub_account = user.is_sub_user()
        if sub_account:
            return sub_account.main_user.account_balance()
        else:
            return user.account_balance()
    except UserInfo.DoesNotExist as ex:
        print(ex)
        return 0


# qImQnB-lUyW3iWL4KPvwqBwLsexhZSbVKIJhGqrdKhQ	充电开始通知
# {{first.DATA}}
# 开始时间：{{keyword1.DATA}}
# 消费单号：{{keyword2.DATA}}
# 充电位置：{{keyword3.DATA}}
# 插座编号：{{keyword4.DATA}}
# 账户余额：{{keyword5.DATA}}
# {{remark.DATA}}

def send_charging_start_message_to_user(order):
    """充电开始提醒"""
    template = 'qImQnB-lUyW3iWL4KPvwqBwLsexhZSbVKIJhGqrdKhQ'

    account_balance = get_user_balance(order.openid)
    url = "{}{}?out_trade_no={}".format(settings.ROOT_URL, reverse('order-recharge-status'), order.out_trade_no)
    color = "#173177"
    data = {
        'first': {
            "value": '您好,欢迎使用亚电新能源充电桩!',
            "color": color,
        },
        "keyword1": {
           # "value": order.begin_time.strftime('%Y-%m-%d %H:%M:%S') if order.begin_time else "",
           "value": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
           "color": color,
        },
        "keyword2": {
           "value": order.out_trade_no,
           "color": color,
        },
        "keyword3": {
            "value": order.charg_pile.name,
            "color": color
        },
        "keyword4": {
            "value": order.gun_num,
            "color": color,
        },
        "keyword5": {
            "value": "{}元".format(account_balance),
            "color": color
        },
        "remark": {
           "value": "感谢您的使用。点击查看订单详情",
           "color": color,
       }
    }
    client = wxClient()
    client.message.send_template(user_id=order.openid, template_id=template, url=url, data=data)
    if order.main_openid:
        client.message.send_template(user_id=order.main_openid, template_id=template, url=url, data=data)


# rhHOX9gT02FXaHxINaP6Xoc1v2LkU1VydxRSsDwKBpY	充电结束通知
# {{first.DATA}}
# 结束时间：{{keyword1.DATA}}
# 结束原因：{{keyword2.DATA}}
# 充电时长：{{keyword3.DATA}}
# 消费金额：{{keyword4.DATA}}
# 账户余额：{{keyword5.DATA}}
# {{remark.DATA}}

def send_charging_end_message_to_user(order):
    """充电结束提醒"""
    template = 'rhHOX9gT02FXaHxINaP6Xoc1v2LkU1VydxRSsDwKBpY'

    url = "{}{}?out_trade_no={}".format(settings.ROOT_URL, reverse('order-recharge-status'), order.out_trade_no)
    color = "#173177"
    data = {
        'first': {
            "value": '您的充电订单已经结束!',
            "color": color,
        },
        "keyword1": {
           "value": order.end_time.strftime('%Y-%m-%d %H:%M:%S') if order.end_time else "",
           "color": color,
        },
        "keyword2": {
           "value": order.charg_status.name if order.charg_status else "",
           "color": color,
        },
        "keyword3": {
            "value": "{}分钟".format(order.total_minutes()),
            "color": color
        },
        "keyword4": {
            "value": "{}元".format(order.cash_fee),
            "color": color,
        },
        "keyword5": {
            "value": "{}元".format(order.balance),
            "color": color
        },
        "remark": {
           "value": "感谢您的使用。点击查看订单详情",
           "color": color
       }
    }
    client = wxClient()
    client.message.send_template(user_id=order.openid, template_id=template, url=url, data=data)
    if order.main_openid:
        client.message.send_template(user_id=order.main_openid, template_id=template, url=url, data=data)