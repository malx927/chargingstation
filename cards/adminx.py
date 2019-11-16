# coding=utf-8
import xadmin
from cards.models import CardUser, ChargingCard, CardRecharge
from xadmin.layout import Fieldset, Row, AppendedText


class CardUserAdmin(object):
    """储值卡用户"""
    list_display = ['name', 'password', 'telephone', 'address', 'bank', 'account', 'is_active', 'add_time']
    search_fields = ['name', 'telephone', 'address', 'bank', 'account']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False


xadmin.site.register(CardUser, CardUserAdmin)


class ChargingCardAdmin(object):
    """储值卡"""
    list_display = ['card_num', 'money', 'status', 'user', 'start_date', 'end_date', 'add_time', 'startup']
    search_fields = ['card_num']
    list_filter = ['status', 'user', 'start_date']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    readonly_fields = ["money"]
    object_list_template = "cards/cards_model_list.html"
    list_display_links_details = True

    form_layout = (
        Fieldset(
            '储值卡信息',
            Row('card_num', 'money'),
            Row('status', 'user'),
            Row('sec_num', "cipher"),
        ),
        Fieldset(
            '有效期限',
            Row('start_date', "end_date"),
        ),
    )


xadmin.site.register(ChargingCard, ChargingCardAdmin)


class CardRechargeAdmin(object):
    """储值卡充值"""
    list_display = ['card', 'user', 'money', 'op_user', 'add_time']
    search_fields = ['card__card_num']
    readonly_fields = ['card', 'user', 'money', 'op_user']
    list_filter = ['user']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False

    def has_add_permission(self):
        return False

    def has_change_permission(self, obj=None):
        return False

    def has_delete_permission(self, obj=None):
        return False


xadmin.site.register(CardRecharge, CardRechargeAdmin)