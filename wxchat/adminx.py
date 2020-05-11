# -*-coding:utf-8-*-

import xadmin
from xadmin import views
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper, AppendedText
from .models import UserInfo, WxPayResult, WxUnifiedOrderResult, GroupClients, Menu, RechargeRecord, RechargeList, \
    UserCollection, SubAccount, SubAccountConsume, UserAcountHistory


class GroupClientsAdmin(object):
    """
    集团大客户
    """
    list_display = ['name', 'contact_man', 'telephone', 'address', 'bank_name', 'account_name', 'account_number', 'tax_number', 'legal_person', ]
    search_fields = ['name', 'telephone', 'account_name', 'legal_person']
    model_icon = 'fa fa-weixin'
    form_layout = (
        Main(
            Fieldset('基本信息',
                Row('name', 'telephone'),
                Row('contact_man', 'address'),
                     Row('legal_person', 'id_card'),
            ),
            Fieldset('公司银行信息',
                Row('bank_name', 'account_name'),
                Row('account_number', 'tax_number'),
            ),
            Fieldset('其他信息',
                Row(
                    AppendedText('subscribe_fee', '元'),
                    AppendedText('occupy_fee', '元')
                ),
                Row(AppendedText('low_fee', '元'), 'low_restrict'),
            ),
        ),
        Side(
            Fieldset("优惠方案", "dicount", "is_reduction", AppendedText("purchase_amount", "元"), AppendedText("reduction", "元")),
        )
    )


xadmin.site.register(GroupClients, GroupClientsAdmin)


class UserInfoAdmin(object):
    """
    充电(微信)用户
    """
    list_display = ['name', 'nickname', 'openid', 'user_type', 'seller', 'binding_amount', 'telephone', 'total_money',
                    'consume_money', 'account_balance']
    search_fields = ['name', 'openid', 'telephone', 'nickname']
    list_filter = ['user_type', 'seller']
    list_per_page = 50
    style_fields = {"is_freeze": "radio-inline"}
    model_icon = 'fa fa-weixin'

    form_layout = (
        Main(
            Fieldset('',
                Row('name', 'nickname'),
                Row('user_type', 'telephone'),
                Row('seller', 'openid'),
                Row('car_number', 'car_type'),
                Row('id_card', None),
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
            AppendedText('total_money', '元'),
            AppendedText('consume_money', '元'),
            AppendedText('binding_amount', '元'),
        )
    )


xadmin.site.register(UserInfo, UserInfoAdmin)


class SubAccountConsumeInline(object):
    model = SubAccountConsume
    style = "table"
    extra = 1


class SubAccountAdmin(object):
    """附属账号"""
    list_display = ['sub_user', 'main_user', 'update_time', 'create_time']
    search_fields = ['sub_user__nickname', 'sub_user__name', 'main_user__nickname', 'main_user__name']
    list_per_page = 50
    show_all_rel_details = False
    model_icon = 'fa fa-weixin'
    inlines = [SubAccountConsumeInline]


xadmin.site.register(SubAccount, SubAccountAdmin)


# class SubAccountHisAdmin(object):
#     """附属账号充值记录"""
#     list_display = ['sub_user', 'main_user', 'recharge_amount', 'balance', 'create_time']
#     search_fields = ['sub_user__nickname', 'sub_user__name', 'main_user__nicknam', 'main_user__name']
#     readonly_fields = ['sub_user', 'main_user', 'recharge_amount', 'balance', 'create_time']
#     list_per_page = 50
#     show_all_rel_details = False
#     model_icon = 'fa fa-weixin'
#     form_layout = (
#         Row('main_user', 'sub_user'),
#         Row('recharge_amount', 'balance'),
#     )
#
#
# xadmin.site.register(SubAccountHis, SubAccountHisAdmin)


# 微信统一支付结果
class WxUnifiedOrderResultAdmin(object):
    list_display = ('return_code', 'appid', 'mch_id', 'device_info', 'result_code', 'err_code', 'trade_type',
                    'prepay_id', 'code_url')
    search_fields = ['prepay_id']
    list_per_page = 50
    model_icon = 'fa fa-weixin'


xadmin.site.register(WxUnifiedOrderResult, WxUnifiedOrderResultAdmin)


# 微信支付结果
class WxPayResultAdmin(object):
    list_display = ('return_code', 'appid', 'mch_id', 'device_info', 'result_code', 'err_code', 'openid',
                    'is_subscribe', 'trade_type', 'total_fee', 'cash_fee', 'transaction_id', 'out_trade_no')
    search_fields = ['transaction_id', 'out_trade_no', 'openid']
    list_per_page = 50
    model_icon = 'fa fa-weixin'


xadmin.site.register(WxPayResult, WxPayResultAdmin)


class MenuAdmin(object):
    list_display = []
    object_list_template = "wxchat/menu.html"
    model_icon = 'fa fa-weixin'


xadmin.site.register(Menu, MenuAdmin)


class RechargeRecordAdmin(object):
    """
    用户充值记录表
    """
    list_display = ('out_trade_no', 'name', 'recharge_type', 'pay_time', 'total_fee', 'cash_fee', 'status')
    search_fields = ['out_trade_no', 'name']
    list_per_page = 50
    model_icon = 'fa fa-weixin'


xadmin.site.register(RechargeRecord, RechargeRecordAdmin)


class RechargeListAdmin(object):
    """用户充值设置"""
    list_display = ('money', 'create_at')
    list_per_page = 50
    model_icon = 'fa fa-weixin'


xadmin.site.register(RechargeList, RechargeListAdmin)


class UserCollectionAdmin(object):
    """用户收藏设置"""
    list_display = ['openid', 'station', 'create_at']
    list_per_page = 50
    model_icon = 'fa fa-weixin'


xadmin.site.register(UserCollection, UserCollectionAdmin)


class UserAcountHistoryAdmin(object):
    """
    客户账号历史记录
    """
    list_display = ['name', 'openid', 'total_money', 'consume_money', 'binding_amount', 'account_balance', 'create_time']
    readonly_fields = ['name', 'openid', 'total_money', 'consume_money', 'binding_amount']
    list_per_page = 50
    model_icon = 'fa fa-weixin'


xadmin.site.register(UserAcountHistory, UserAcountHistoryAdmin)