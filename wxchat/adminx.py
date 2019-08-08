# -*-coding:utf-8-*-
__author__ = 'Administrator'
import xadmin
from xadmin import views
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper, AppendedText
from .models import UserInfo, WxPayResult, WxUnifiedOrderResult, GroupClients, Menu, RechargeRecord, RechargeList, \
    UserCollection


class GroupClientsAdmin(object):
    """
    集团大客户
    """
    list_display = ['name', 'bank_name', 'account_name', 'account_number', 'tax_number', 'legal_person', 'telephone', 'address',
                    'fee_scale']
    search_fields = ['name', 'telephone', 'account_name', 'legal_person']
    model_icon = 'fa fa-paypal'
    form_layout = (
        Main(
            Fieldset('基本信息',
                Row('name', 'short_name'),
                Row('address', 'contact_info'),
                Row('contact_man', 'telephone'),
            ),
            Fieldset('公司银行信息',
                Row('bank_name', 'account_name'),
                Row('account_number', 'tax_number'),
            ),
            Fieldset('法人信息',
                Row('legal_person', 'id_card'),
            ),
            Fieldset('其他信息',
                Row(
                    AppendedText('subscribe_fee', '元'),
                    AppendedText('occupy_fee', '元')
                ),
                Row(AppendedText('low_fee', '元'), 'low_restrict'),
                'user'
            ),
        ),
        Side(
            Fieldset("优惠方案", "fee_scale", "dicount", "is_reduction", AppendedText("purchase_amount", "元"), AppendedText("reduction", "元")),
        )
    )


xadmin.site.register(GroupClients, GroupClientsAdmin)


class UserInfoAdmin(object):
    """
    充电(微信)用户
    """
    list_display = ['name', 'nickname', 'openid', 'user_type', 'seller', 'group_client', 'binding_amount', 'telephone', 'total_money',
                    'consume_money', 'account_balance']
    search_fields = ['name', 'openid', 'telephone']
    list_filter = ['user_type', 'seller', 'group_client']
    list_per_page = 50
    style_fields = {"is_freeze": "radio-inline"}
    model_icon = 'fa fa-weixin'

    form_layout = (
        Main(
            Fieldset('',
                Row('name', 'nickname'),
                Row('user_type', 'telephone'),
                Row('seller', 'group_client'),
                Row('id_card', 'openid'),
                Row('car_number', 'car_type'),
                css_class='unsort no_title'
            ),
            Fieldset(
                "微信公众号信息",
                'subscribe',
                'subscribe_time',
                Row('sex', 'subscribe_scene'),
                Row('country', 'province'),
                Row('city', 'language'),
                Row('headimgurl', 'qr_scene'),
            ),
            Fieldset(
                "其他信息",
                Row('last_charg_time', 'out_trade_no'),
                Row('visit_city', 'visit_time'),
                Row('is_freeze', 'freeze_time'),
                'freeze_reason',
            )
        ),
        Side(
            'ic_card', 'ic_pwd',
            AppendedText('total_money', '元'),
            AppendedText('consume_money', '元'),
            AppendedText('binding_amount', '元'),
        )
    )


xadmin.site.register(UserInfo, UserInfoAdmin)


# 微信统一支付结果
class WxUnifiedOrderResultAdmin(object):
    list_display = ('return_code', 'appid', 'mch_id', 'device_info', 'result_code', 'err_code', 'trade_type',
                    'prepay_id', 'code_url')
    search_fields = ['prepay_id']
    list_per_page = 50
    model_icon = 'fa fa-file-text-o'


xadmin.site.register(WxUnifiedOrderResult, WxUnifiedOrderResultAdmin)


# 微信支付结果
class WxPayResultAdmin(object):
    list_display = ('return_code', 'appid', 'mch_id', 'device_info', 'result_code', 'err_code', 'openid',
                    'is_subscribe', 'trade_type', 'total_fee', 'cash_fee', 'transaction_id', 'out_trade_no')
    search_fields = ['transaction_id', 'out_trade_no']
    list_per_page = 50
    model_icon = 'fa fa-check-square'


xadmin.site.register(WxPayResult, WxPayResultAdmin)


class MenuAdmin(object):
    list_display = []
    object_list_template = "wxchat/menu.html"


xadmin.site.register(Menu, MenuAdmin)


class RechargeRecordAdmin(object):
    """
    用户充值记录表
    """
    list_display = ('out_trade_no', 'name', 'account_number', 'recharge_type', 'pay_bank', 'total_fee', 'cash_fee', 'status')
    search_fields = ['out_trade_no', 'name']
    list_per_page = 50
    model_icon = 'fa fa-check-square'


xadmin.site.register(RechargeRecord, RechargeRecordAdmin)


class RechargeListAdmin(object):
    """用户充值设置"""
    list_display = ('money', 'create_at')
    list_per_page = 50
    model_icon = 'fa fa-check-square'


xadmin.site.register(RechargeList, RechargeListAdmin)


class UserCollectionAdmin(object):
    """用户充值设置"""
    list_display = ['openid', 'station', 'create_at']
    list_per_page = 50
    model_icon = 'fa fa-check-square'


xadmin.site.register(UserCollection, UserCollectionAdmin)