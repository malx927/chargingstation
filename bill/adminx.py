# coding=utf8

import xadmin
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper, AppendedText, Col, TabHolder, Tab

from .models import InvoiceTitle, UserRefund, WxRefundRecord


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
    list_display = ["out_refund_no", "name", "nickname", "out_trade_no", "total_fee", "refund_fee", "refund_id", 'status']
    search_fields = ['out_refund_no', 'name', 'out_trade_no', 'refund_id']
    list_filter = ['status']
    model_icon = 'fa fa-random'

    form_layout = (
        Fieldset(
            '用户退款信息',
            Row('out_refund_no', 'name'),
            Row('nickname', 'openid'),
            Row('telephone', 'out_trade_no'),
            Row('transaction_id', 'refund_id'),
            Row('refund_fee', 'total_fee'),
            Row('status', 'update_time'),
        ),
    )

    def has_add_permission(self):
        return False

    def has_change_permission(self, obj=None):
        return False

    def has_delete_permission(self, obj=None):
        return False


xadmin.site.register(UserRefund, UserRefundAdmin)


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
