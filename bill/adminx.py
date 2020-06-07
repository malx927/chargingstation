# coding=utf8

import xadmin
from django.urls import reverse
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper, AppendedText, Col, TabHolder, Tab

from .models import InvoiceTitle, UserRefund, WxRefundRecord, UserRefundDetail


class InvoiceTitleAdmin(object):
    """
    发票抬头信息
    """
    list_display = ["title", "category", "tax_number", "address", "telephone", "bank_account", "email", "invoice_style"]
    search_fields = ["OperatorName"]
    model_icon = 'fa fa-random'

    form_layout = (
            Fieldset(
                '发票抬头信息',
                Row('title', 'category'),
                Row('tax_number', 'telephone'),
                Row('address'),
                Row('bank_account'),
                Row('email', 'invoice_style'),
            ),
    )

    def get_media(self):
        media = super().get_media()
        path = self.request.get_full_path()
        if "add" in path or 'update' in path:
            media.add_css({'screen': ('bill/bill.css',)})
            # media.add_js([self.static('stationmanager/js/xadmin.areacode.js')])
        return media


xadmin.site.register(InvoiceTitle, InvoiceTitleAdmin)


class UserRefundAdmin(object):
    list_display = ["code", "name", "nickname", "telephone", 'openid', "refund_fee", 'status', "refund"]
    search_fields = ["code", 'openid', 'name', 'nickname', 'telephone']
    list_filter = ['status']
    model_icon = 'fa fa-random'
    object_list_template = "bill/refund_model_list.html"

    def has_add_permission(self):
        return False

    def has_change_permission(self, obj=None):
        return False

    def has_delete_permission(self, obj=None):
        return False

    def refund(self, instance):
        url = reverse("wxchat-apply-refund-list")
        unfreeze_url = reverse("wxchat-user-unfreeze")
        refund_url = "{}?openid={}&id={}".format(url, instance.openid, instance.id)
        unfreeze_url = "{}?openid={}".format(unfreeze_url, instance.openid)
        refund_btn = "<a class='btn btn-xs btn-danger' data-toggle='modal' data-target='#myModal' data-uri='{}'>退款</a> ".format(refund_url)
        unfreeze_btn = " <a class='btn btn-xs btn-primary unfreeze-btn' data-uri='{}'>解冻</a>".format(unfreeze_url)
        return refund_btn + unfreeze_btn

    refund.short_description = "操作"
    refund.allow_tags = True
    refund.is_column = True


xadmin.site.register(UserRefund, UserRefundAdmin)


class UserRefundDetailAdmin(object):
    list_display = ["out_refund_no", "user_refund", 'openid', "out_trade_no", "transaction_id", "refund_fee", "refund_id", "update_time", 'status']
    search_fields = ['openid', 'user_refund__name', 'user_refund__nickname', 'out_trade_no', 'out_refund_no', 'refund_id', 'transaction_id']
    list_filter = ['status']
    model_icon = 'fa fa-random'

    # def has_add_permission(self):
    #     return False
    #
    # def has_change_permission(self, obj=None):
    #     return False
    #
    # def has_delete_permission(self, obj=None):
    #     return False


xadmin.site.register(UserRefundDetail, UserRefundDetailAdmin)


class WxRefundRecordAdmin(object):
    list_display = ["return_code", "result_code", "appid", "mch_id", "out_trade_no", "out_refund_no", "refund_id", "refund_fee", "total_fee", 'return_msg']
    search_fields = ['out_trade_no', 'out_refund_no', 'refund_id', 'transaction_id']
    model_icon = 'fa fa-random'

    form_layout = (
        Fieldset(
            '微信退款日志',
            Row('return_code', 'return_msg'),
            Row('result_code', 'err_code'),
            Row('err_code_des', 'appid'),
            Row('mch_id', 'nonce_str'),
            Row('sign', 'transaction_id'),
            Row('out_trade_no', 'out_refund_no'),
            Row('refund_id', 'refund_fee'),
            Row('settlement_refund_fee', 'total_fee'),
            Row('settlement_total_fee', 'fee_type'),
            Row('cash_fee', 'cash_fee_type'),
            Row('cash_refund_fee'),
        ),
    )

    def has_add_permission(self):
        return False

    def has_change_permission(self, obj=None):
        return False

    def has_delete_permission(self, obj=None):
        return False


xadmin.site.register(WxRefundRecord, WxRefundRecordAdmin)
