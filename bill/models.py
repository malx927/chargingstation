from django.db import models


class InvoiceTitle(models.Model):
    """发票抬头"""
    CATEGORY = (
        (0, '公司发票'),
        (1, '个人发票')
    )
    INVOICE_STYLE = (
        (0, '电子发票'),
        (1, '纸质发票')
    )
    title = models.CharField(verbose_name='发票抬头', max_length=128)
    category = models.IntegerField(verbose_name='发票类型', default=0, choices=CATEGORY)
    tax_number = models.CharField(verbose_name='税务识别号', max_length=64, blank=True, null=True)
    address = models.CharField(verbose_name='地址', max_length=128, blank=True, null=True)
    telephone = models.CharField(verbose_name='电话', max_length=32, blank=True, null=True)
    bank_account = models.CharField(verbose_name='开户行及账号', max_length=256, blank=True, null=True)
    email = models.CharField(verbose_name='邮箱', max_length=128, blank=True, null=True)
    invoice_style = models.IntegerField(verbose_name='发票介质', blank=True, null=True, choices=INVOICE_STYLE)
    update_time = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    add_time = models.DateTimeField(verbose_name="添加时间", auto_now_add=True)

    class Meta:
        verbose_name = '发票抬头管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class UserRefund(models.Model):
    """
    用户退款记录
    """
    REFUND_STATUS = (
        (0, '失败'),
        (1, '成功')
    )
    out_refund_no = models.CharField(verbose_name='退款单号', max_length=64)
    name = models.CharField(verbose_name='姓名', max_length=24, blank=True, null=True)
    nickname = models.CharField(verbose_name='昵称', max_length=64, help_text="微信昵称")
    openid = models.CharField(verbose_name='微信ID', max_length=120, blank=True, null=True)
    telephone = models.CharField(verbose_name='手机号码', max_length=18, blank=True, default='')
    out_trade_no = models.CharField(verbose_name='订单编号', max_length=32)
    transaction_id = models.CharField(verbose_name='微信支付订单号', max_length=32, null=True, blank=True)
    total_fee = models.DecimalField(verbose_name='订单金额', max_digits=7, decimal_places=2, blank=True, null=True)
    refund_fee = models.DecimalField(verbose_name='退款金额', max_digits=7, decimal_places=2, blank=True, null=True)
    refund_id = models.CharField(verbose_name='退款单号', max_length=32, blank=True, null=True)
    status = models.IntegerField(verbose_name='退款状态', choices=REFUND_STATUS, blank=True, null=True)
    update_time = models.DateTimeField(verbose_name='退款时间', blank=True, null=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户退款记录'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.out_refund_no


class WxRefundRecord(models.Model):
    """
    微信退款日志
    """
    return_code = models.CharField(verbose_name='返回状态码', max_length=16, null=True, blank=True)
    return_msg = models.CharField(verbose_name='返回信息', max_length=128, null=True, blank=True)
    result_code = models.CharField(verbose_name='业务结果', max_length=16, null=True, blank=True)
    err_code = models.CharField(verbose_name='错误代码', max_length=32, null=True, blank=True)
    err_code_des = models.CharField(verbose_name='错误代码描述', max_length=128, null=True, blank=True)
    appid = models.CharField(verbose_name='公众账号ID', max_length=32, null=True, blank=True)
    mch_id = models.CharField(verbose_name='商户号', max_length=32, null=True, blank=True)
    nonce_str = models.CharField(verbose_name='随机字符串', max_length=32, null=True, blank=True)
    sign = models.CharField(verbose_name='返回信息', max_length=32, null=True, blank=True)
    transaction_id = models.CharField(verbose_name='微信订单号', max_length=32, null=True, blank=True)
    out_trade_no = models.CharField(verbose_name='商户订单号', max_length=32, null=True, blank=True)
    out_refund_no = models.CharField(verbose_name='退款单号', max_length=64, null=True, blank=True)
    refund_id = models.CharField(verbose_name='微信退款单号', max_length=32)
    refund_fee = models.IntegerField(verbose_name='退款金额', blank=True, null=True)
    settlement_refund_fee = models.IntegerField(verbose_name='应结退款金额', blank=True, null=True)
    total_fee = models.IntegerField(verbose_name='标价金额', blank=True, null=True)
    settlement_total_fee = models.IntegerField(verbose_name='应结订单金额', blank=True, null=True)
    fee_type = models.CharField(verbose_name='标价币种', max_length=8, null=True, blank=True)
    cash_fee = models.IntegerField(verbose_name='现金支付金额', blank=True, null=True)
    cash_fee_type = models.CharField(verbose_name='标价币种', max_length=16, null=True, blank=True)
    cash_refund_fee = models.IntegerField(verbose_name='现金退款金额', blank=True, null=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '微信退款日志'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.refund_id