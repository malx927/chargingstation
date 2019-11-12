# coding=utf-8
import xadmin
from cards.models import CardUser, ChargingCard
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
    list_display = ['card_num', 'money', 'status', 'user', 'start_date', 'end_date', 'add_time']
    search_fields = ['card_num']
    list_filter = ['status', 'user', 'start_date']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False

    form_layout = (
        Fieldset(
            '储值卡信息',
            Row('card_num', AppendedText('money', '元')),
            Row('status', 'user'),
            Row('sec_num', "cipher"),
        ),
        Fieldset(
            '有效期限',
            Row('start_date', "end_date"),
        ),

    )


xadmin.site.register(ChargingCard, ChargingCardAdmin)