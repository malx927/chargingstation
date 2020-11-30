from django.db import models


class InvoiceTitle(models.Model):
    """发票抬头"""
    CATEGORY = (
        (0, '公司发票'),
        (1, '个人发票')
    )
    INVOICE_WRITE = (
        (0, '未开'),
        (1, '已开')
    )
    openid = models.CharField(verbose_name='微信ID', max_length=120, blank=True, null=True)
    name = models.CharField(verbose_name='姓名', max_length=64, blank=True, null=True)
    title = models.CharField(verbose_name='发票抬头', max_length=128)
    category = models.IntegerField(verbose_name='发票类型', default=0, choices=CATEGORY)
    tax_number = models.CharField(verbose_name='税务识别号', max_length=64, blank=True, null=True)
    address = models.CharField(verbose_name='地址', max_length=128, blank=True, null=True)
    telephone = models.CharField(verbose_name='电话', max_length=32, blank=True, null=True)
    bank_account = models.CharField(verbose_name='开户行及账号', max_length=256, blank=True, null=True)
    email = models.CharField(verbose_name='邮箱', max_length=128, blank=True, null=True)
    total_money = models.DecimalField(verbose_name='充值总额', default=0, blank=True, max_digits=8, decimal_places=2)
    consume_money = models.DecimalField(verbose_name='消费总额', default=0, blank=True, max_digits=8, decimal_places=2)
    is_write = models.IntegerField(verbose_name='开票确认', default=0, choices=INVOICE_WRITE)
    update_time = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    add_time = models.DateTimeField(verbose_name="申请时间", auto_now_add=True)

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
        (0, '未退款'),
        (1, '已退款')
    )
    code = models.CharField(verbose_name='申请单号', max_length=32)
    openid = models.CharField(verbose_name='微信ID', max_length=120)
    name = models.CharField(verbose_name='姓名', max_length=24, blank=True, null=True)
    nickname = models.CharField(verbose_name='昵称', max_length=64, help_text="微信昵称")
    telephone = models.CharField(verbose_name='手机号码', max_length=18, blank=True, default='')
    refund_fee = models.DecimalField(verbose_name='退款金额(元)', max_digits=7, decimal_places=2, default=0)
    actual_fee = models.DecimalField(verbose_name='实退金额(元)', max_digits=7, decimal_places=2, default=0)
    status = models.IntegerField(verbose_name='退款状态', choices=REFUND_STATUS, default=0)
    update_time = models.DateTimeField(verbose_name='退款时间', blank=True, null=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户退款申请'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.code


class UserRefundDetail(models.Model):
    """
    用户退款明细
    """
    REFUND_STATUS = (
        (0, '失败'),
        (1, '成功')
    )
    out_refund_no = models.CharField(verbose_name='退款单号', max_length=64)
    user_refund = models.ForeignKey(UserRefund, verbose_name='申请单号', blank=True, null=True, on_delete=models.SET_NULL, db_constraint=False)
    openid = models.CharField(verbose_name='微信ID', max_length=120, blank=True, null=True)
    out_trade_no = models.CharField(verbose_name='原订单编号', max_length=128)
    transaction_id = models.CharField(verbose_name='原微信订单号', max_length=128, null=True, blank=True)
    total_fee = models.DecimalField(verbose_name='订单金额(元)', max_digits=7, decimal_places=2, blank=True, null=True)
    refund_fee = models.DecimalField(verbose_name='退款金额(元)', max_digits=7, decimal_places=2, blank=True, null=True)
    refund_id = models.CharField(verbose_name='微信退款单号', max_length=32, blank=True, null=True)
    status = models.IntegerField(verbose_name='退款状态', choices=REFUND_STATUS, blank=True, null=True)
    update_time = models.DateTimeField(verbose_name='退款时间', blank=True, null=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户退款明细'
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
    refund_channel = models.CharField(verbose_name='微信退款单号', max_length=16, null=True, blank=True)
    refund_fee = models.IntegerField(verbose_name='退款金额(分)', blank=True, null=True)
    settlement_refund_fee = models.IntegerField(verbose_name='应结退款金额(分)', blank=True, null=True)
    total_fee = models.IntegerField(verbose_name='标价金额(分)', blank=True, null=True)
    settlement_total_fee = models.IntegerField(verbose_name='应结订单金额(分)', blank=True, null=True)
    fee_type = models.CharField(verbose_name='标价币种', max_length=8, null=True, blank=True)
    cash_fee = models.IntegerField(verbose_name='现金支付金额(分)', blank=True, null=True)
    cash_fee_type = models.CharField(verbose_name='标价币种', max_length=16, null=True, blank=True)
    cash_refund_fee = models.IntegerField(verbose_name='现金退款金额(分)', blank=True, null=True)
    coupon_refund_fee = models.IntegerField(verbose_name='代金券退款总金额', null=True, blank=True)
    coupon_refund_count = models.IntegerField(verbose_name='退款代金券使用数量', null=True, blank=True)
    coupon_type_0 = models.CharField(verbose_name='代金券类型1', max_length=8, null=True, blank=True)
    coupon_refund_fee_0 = models.IntegerField(verbose_name='单个代金券退款金额', null=True, blank=True)
    coupon_refund_id_0 = models.CharField(verbose_name='退款代金券ID', max_length=20, null=True, blank=True)
    coupon_type_1 = models.CharField(verbose_name='代金券类型1', max_length=8, null=True, blank=True)
    coupon_refund_fee_1 = models.IntegerField(verbose_name='单个代金券退款金额', null=True, blank=True)
    coupon_refund_id_1 = models.CharField(verbose_name='退款代金券ID', max_length=20, null=True, blank=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '微信退款日志'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.refund_id