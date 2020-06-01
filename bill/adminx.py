# coding=utf8

import xadmin

from .models import InvoiceTitle, UserRefund, WxRefundRecord


class InvoiceTitleAdmin(object):
    """
    发票抬头信息
    """
    list_display = ["title", "category", "tax_number", "address", "telephone", "bank_account", "email", "invoice_style"]
    search_fields = ["OperatorName"]
    model_icon = 'fa fa-random'
    list_export = ('xls', 'xml', 'json')


xadmin.site.register(InvoiceTitle, InvoiceTitleAdmin)


class UserRefundAdmin(object):
    list_display = ["out_refund_no", "name", "nickname", "out_trade_no", "total_fee", "refund_fee", "refund_id", 'status']
    search_fields = ['out_refund_no', 'name', 'out_trade_no', 'refund_id']
    list_filter = ['status']
    model_icon = 'fa fa-random'


xadmin.site.register(UserRefund, UserRefundAdmin)


class WxRefundRecordAdmin(object):
    list_display = ["return_code", "result_code", "appid", "mch_id", "out_trade_no", "out_refund_no", "refund_id", "refund_fee", "total_fee", 'return_msg']
    search_fields = ['out_trade_no', 'out_refund_no', 'refund_id', 'transaction_id']
    model_icon = 'fa fa-random'


xadmin.site.register(WxRefundRecord, WxRefundRecordAdmin)
