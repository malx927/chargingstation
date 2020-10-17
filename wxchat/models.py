# -*-coding:utf-8-*-
import datetime

from django.contrib.auth.models import Group
from django.db import models
from django.conf import settings
from django.urls import reverse

from codingmanager.constants import *
from codingmanager.models import PriceType
# Create your models here.
from django.db.models import Max, Count, Sum
from django.utils.safestring import mark_safe
from stationmanager.models import Seller, Station, ChargingPile


class GroupClients(models.Model):
    """
    集团大客户
    """
    name = models.CharField(verbose_name='集团名称', max_length=64)
    bank_name = models.CharField(verbose_name='开户银行', max_length=100, blank=True, null=True)
    account_name = models.CharField(verbose_name='银行账户名', max_length=36, blank=True, null=True)
    account_number = models.CharField(verbose_name='银行账号', max_length=24, blank=True, null=True)
    tax_number = models.CharField(verbose_name='税号', max_length=24, blank=True, null=True)
    legal_person = models.CharField(verbose_name='法人代表', max_length=24, blank=True, null=True)
    id_card = models.CharField(verbose_name='身份证号', max_length=20, blank=True, null=True)
    address = models.CharField(verbose_name='联系地址', max_length=120, blank=True, null=True)
    contact_man = models.CharField(verbose_name='联系人', max_length=64, blank=True, null=True)
    telephone = models.CharField(verbose_name='手机号码', max_length=64, blank=True, null=True)
    dicount = models.DecimalField(verbose_name='打折率', max_digits=4, decimal_places=1, default=0, choices=DICOUNT_MODE)
    is_reduction = models.IntegerField(verbose_name='是否满减', default=0, choices=((0, '否'), (1, '是')))
    purchase_amount = models.IntegerField(verbose_name='满减限额值(满)', default=0, help_text='满300减50')
    reduction = models.IntegerField(verbose_name='减免额度(减)', default=0)
    subscribe_fee = models.DecimalField(verbose_name='预约费', max_digits=6, decimal_places=2, default=0)
    occupy_fee = models.DecimalField(verbose_name='占位费', max_digits=6, decimal_places=2, default=0)
    low_fee = models.DecimalField(verbose_name='小电流补偿费', max_digits=6, decimal_places=2, default=0)
    low_restrict = models.IntegerField(verbose_name='开启小电流限制', default=0, choices=((0, '关闭'), (1, '开启')))
    update_time = models.DateTimeField(verbose_name='添加时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '集团大客户信息'
        verbose_name_plural = verbose_name


class UserInfo(models.Model):
    """
    充电用户信息(公众号号)
    """
    name = models.CharField(verbose_name='姓名', max_length=24, blank=True, null=True)
    nickname = models.CharField(verbose_name='昵称', max_length=64, help_text="微信昵称")
    openid = models.CharField(verbose_name='微信ID', max_length=120, blank=True, null=True)
    user_type = models.IntegerField(verbose_name='用户类型', choices=USER_TYPE_CHOICE, default=0)
    seller = models.ForeignKey(Seller, verbose_name='运营商', blank=True, null=True, on_delete=models.SET_NULL, db_constraint=False)
    id_card = models.CharField(verbose_name='身份证号', max_length=20, blank=True, default='')
    telephone = models.CharField(verbose_name='手机号码', max_length=18, blank=True, default='')
    # ic_card = models.CharField(verbose_name='IC卡号', max_length=24, blank=True, default='')
    # ic_pwd = models.CharField(verbose_name='IC卡秘钥', max_length=20, blank=True, default='')
    total_money = models.DecimalField(verbose_name='充值总额(元)', default=0, blank=True, max_digits=8, decimal_places=2, help_text='<font color=red>用户清零请将充值总额和消费总额设置为零</font>')
    consume_money = models.DecimalField(verbose_name='消费总额', default=0, blank=True, max_digits=8, decimal_places=2, help_text='<font color=red>用户清零请将充值总额和消费总额设置为零</font>')
    binding_amount = models.DecimalField(verbose_name='赠送金额(元)', default=0, blank=True, max_digits=6, decimal_places=2)
    consume_amount = models.DecimalField(verbose_name='赠金消费额(元)', default=0, blank=True, max_digits=6, decimal_places=2)
    subscribe = models.NullBooleanField(verbose_name='是否订阅', default=0)
    sex = models.IntegerField(verbose_name='性别', choices=SEX_CHOICE)  # 值为1时是男性，值为2时是女性，值为0时是未知
    province = models.CharField(verbose_name='省份', max_length=64, blank=True, null=True)
    city = models.CharField(verbose_name='城市', max_length=64, blank=True, null=True)
    country = models.CharField(verbose_name='国家', max_length=64, blank=True, null=True)
    language = models.CharField(verbose_name='使用语言', max_length=12, blank=True, null=True)
    headimgurl = models.CharField(verbose_name='头像', max_length=240, blank=True, null=True)
    subscribe_time = models.DateTimeField(verbose_name='注册时间', null=True, blank=True)
    subscribe_scene = models.CharField(verbose_name='渠道来源', max_length=64, blank=True, null=True)
    qr_scene = models.IntegerField(verbose_name='扫码场景', default=0, blank=True, null=True)
    car_number = models.CharField(verbose_name="车牌号", max_length=32, blank=True, null=True)
    car_type = models.CharField(verbose_name="车型", max_length=32, blank=True, null=True)
    last_charg_time = models.DateTimeField(verbose_name='最后充电时间', blank=True, null=True)
    is_freeze = models.IntegerField(verbose_name='是否冻结', default=0, choices=((0, '正常'), (1, '冻结')))  # 1、退款申请 2、反复充停电操作
    freeze_time = models.DateTimeField(verbose_name='冻结时间', blank=True, null=True)  # 1、退款后确认解冻，2、10分钟，3主动停充后，3-5分内停充
    freeze_reason = models.CharField(verbose_name='冻结原因', max_length=128, blank=True, null=True)
    pile_sn = models.CharField(verbose_name='电桩SN', max_length=64, blank=True, null=True)
    gun_num = models.CharField(verbose_name='枪口号', max_length=12, blank=True, null=True)
    out_trade_no = models.CharField(verbose_name='最近一次订单编号', max_length=32, blank=True, null=True)
    visit_city = models.CharField(verbose_name="最后访问地点", max_length=120, blank=True, null=True)
    visit_time = models.DateTimeField(verbose_name="最后访问时间", blank=True, null=True)

    def __str__(self):
        return self.name if self.name else self.nickname

    class Meta:
        verbose_name = u'充电客户信息'
        verbose_name_plural = verbose_name

    def account_balance(self):
        return self.total_money - self.consume_money + self.binding_amount - self.consume_amount

    account_balance.short_description = '账户余额'

    def recharge_balance(self):
        return self.total_money - self.consume_money

    def is_sub_user(self):
        sub_account = self.subaccount_set.first()
        return sub_account

    @classmethod
    def get_max_value(cls):
        obj = cls.objects.all().aggregate(max_id=Max('qr_scene'))

        if obj['max_id']:
            return obj['max_id'] + 1
        else:
            return 1

    def balance_reset(self):
        url = reverse("wxchat-balance-reset")
        reset_url = url + "?user_id={}".format(self.id)
        charging = "<button class='btn btn-xs btn-success' data-toggle='modal' data-target='#myModal' data-uri='{}'>账户清零</a>".format(reset_url)
        return mark_safe(charging)

    balance_reset.short_description = "选项"

    def update_freeze(self, is_freeze, reason):
        self.is_freeze = is_freeze
        if is_freeze == 1:
            self.freeze_time = datetime.datetime.now()
            self.freeze_reason = reason
        else:
            self.freeze_time = None
            self.freeze_reason = None
        self.save(update_fields=['is_freeze', 'freeze_time', 'freeze_reason'])


class RechargeRecord(models.Model):
    """
    用户充值记录表
    """
    out_trade_no = models.CharField(verbose_name='订单编号', max_length=32)
    name = models.CharField(verbose_name='用户名', max_length=24, blank=True, default='')
    recharge_type = models.IntegerField(verbose_name='充值方式', choices=((1, '现金'), (2, '微信')))
    telephone = models.CharField(verbose_name='电话号码', max_length=16, blank=True, default='')
    openid = models.CharField(verbose_name='微信号(openid)', max_length=32)
    transaction_id = models.CharField(verbose_name='微信支付订单号', max_length=32, null=True, blank=True)
    total_fee = models.DecimalField(verbose_name='应收款', max_digits=7, decimal_places=2, blank=True, null=True)
    cash_fee = models.DecimalField(verbose_name='实收款', max_digits=7, decimal_places=2, blank=True, null=True)
    gift_amount = models.IntegerField(verbose_name="赠送金额(元)", default=0)
    pay_time = models.DateTimeField(verbose_name='支付时间', blank=True, null=True)
    refund_fee = models.DecimalField(verbose_name="退款金额", max_digits=7, decimal_places=2, default=0)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True, auto_now=False)
    status = models.IntegerField(verbose_name='支付状态', default=0, choices=PAY_ORDER_STATUS)

    class Meta:
        verbose_name = '用户充值记录'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.out_trade_no


class WxUnifiedOrderResult(models.Model):
    """
    微信统一下单结果
    """
    return_code = models.CharField(verbose_name='返回状态码', max_length=16, null=True, blank=True)
    return_msg = models.CharField(verbose_name='返回信息', max_length=128, null=True, blank=True)

    appid = models.CharField(verbose_name='公众账号ID', max_length=32, null=True, blank=True)
    mch_id = models.CharField(verbose_name='商户号', max_length=32, null=True, blank=True)
    device_info = models.CharField(verbose_name='设备号', max_length=32, null=True, blank=True)
    nonce_str = models.CharField(verbose_name='随机字符串', max_length=32, null=True, blank=True)
    sign = models.CharField(verbose_name='返回信息', max_length=32, null=True, blank=True)
    result_code = models.CharField(verbose_name='业务结果', max_length=16, null=True, blank=True)
    err_code = models.CharField(verbose_name='错误代码', max_length=32, null=True, blank=True)
    err_code_des = models.CharField(verbose_name='错误代码描述', max_length=128, null=True, blank=True)

    trade_type = models.CharField(verbose_name='交易类型', max_length=16, null=True, blank=True)
    prepay_id = models.CharField(verbose_name='预支付会话标识', max_length=64, null=True, blank=True)
    code_url = models.CharField(verbose_name='二维码链接', max_length=64, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, auto_now=False)

    class Meta:
        verbose_name = '微信统一下单结果'
        verbose_name_plural = verbose_name

    def __str__(self):
        return '预支付标识:{0}({1})'.format(self.prepay_id, self.mch_id)


class WxPayResult(models.Model):
    """
    微信支付结果
    """
    return_code = models.CharField(verbose_name='返回状态码', max_length=16, null=True, blank=True)
    return_msg = models.CharField(verbose_name='返回信息', max_length=128, null=True, blank=True)
    appid = models.CharField(verbose_name='公众账号ID', max_length=32, null=True, blank=True)
    mch_id = models.CharField(verbose_name='商户号', max_length=32, null=True, blank=True)
    device_info = models.CharField(verbose_name='设备号', max_length=32, null=True, blank=True)
    nonce_str = models.CharField(verbose_name='随机字符串', max_length=32, null=True, blank=True)
    sign = models.CharField(verbose_name='返回信息', max_length=32, null=True, blank=True)
    sign_type = models.CharField(verbose_name='返回信息', max_length=32, null=True, blank=True)
    result_code = models.CharField(verbose_name='业务结果', max_length=16, null=True, blank=True)
    err_code = models.CharField(verbose_name='错误代码', max_length=32, null=True, blank=True)
    err_code_des = models.CharField(verbose_name='错误代码描述', max_length=128, null=True, blank=True)
    openid = models.CharField(verbose_name='用户标识', max_length=128, null=True, blank=True)
    is_subscribe = models.CharField(verbose_name='是否关注公众账号', max_length=1, null=True, blank=True)
    trade_type = models.CharField(verbose_name='交易类型', max_length=16, null=True, blank=True)
    bank_type = models.CharField(verbose_name='付款银行', max_length=16, null=True, blank=True)
    total_fee = models.IntegerField(verbose_name='订单金额', null=True, blank=True)
    settlement_total_fee = models.IntegerField(verbose_name='应结订单金额', null=True, blank=True)
    fee_type = models.CharField(verbose_name='货币种类', max_length=8, null=True, blank=True)
    cash_fee = models.IntegerField(verbose_name='现金支付金额', null=True, blank=True)
    cash_fee_type = models.CharField(verbose_name='现金支付货币类型', max_length=16, null=True, blank=True)
    coupon_fee = models.IntegerField(verbose_name='总代金券金额', null=True, blank=True)
    coupon_count = models.IntegerField(verbose_name='代金券使用数量', null=True, blank=True)
    coupon_type_0 = models.CharField(verbose_name='代金券类型', max_length=16, null=True, blank=True)
    coupon_id_0 = models.CharField(verbose_name='代金券ID', max_length=20, null=True, blank=True)
    coupon_fee_0 = models.IntegerField(verbose_name='单个代金券支付金额', null=True, blank=True)
    coupon_type_1 = models.CharField(verbose_name='代金券类型', max_length=16, null=True, blank=True)
    coupon_id_1 = models.CharField(verbose_name='代金券ID', max_length=20, null=True, blank=True)
    coupon_fee_1 = models.IntegerField(verbose_name='单个代金券支付金额', null=True, blank=True)
    transaction_id = models.CharField(verbose_name='微信支付订单号', max_length=32, null=True, blank=True)
    out_trade_no = models.CharField(verbose_name='商户订单号', max_length=32, null=True, blank=True)
    attach = models.CharField(verbose_name='商家数据包', max_length=128, null=True, blank=True)
    time_end = models.CharField(verbose_name='支付完成时间', max_length=14, null=True, blank=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '微信支付结果'
        verbose_name_plural = verbose_name

    def __str__(self):
        return '订单号:{0}({1})'.format(self.transaction_id, self.out_trade_no)


class UserAcountHistory(models.Model):
    """
    客户账号历史记录
    """
    name = models.CharField(verbose_name='用户名', max_length=64, help_text="姓名或者微信昵称")
    openid = models.CharField(verbose_name='微信ID', max_length=120, blank=True, null=True)
    total_money = models.DecimalField(verbose_name='充值总额', default=0, blank=True, max_digits=8, decimal_places=2)
    consume_money = models.DecimalField(verbose_name='消费总额', default=0, blank=True, max_digits=8, decimal_places=2)
    binding_amount = models.DecimalField(verbose_name='赠送金额', default=0, blank=True, max_digits=6, decimal_places=2)
    consume_amount = models.DecimalField(verbose_name='赠金消费', default=0, blank=True, max_digits=6, decimal_places=2)
    create_time = models.DateTimeField(verbose_name="添加时间", auto_now_add=True)

    def account_balance(self):
        return self.total_money - self.consume_money + self.binding_amount - self.consume_amount

    account_balance.short_description = '账户余额'

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = u'客户账号历史记录'
        verbose_name_plural = verbose_name


class Menu(models.Model):
    """
    微信菜单设置
    """

    class Meta:
        verbose_name = "微信菜单维护"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.Meta.verbose_name


class RechargeList(models.Model):
    money = models.IntegerField(verbose_name="充值金额(元)", default=0)
    gift_amount = models.IntegerField(verbose_name="赠送金额(元)", default=0)
    create_at = models.DateTimeField(verbose_name='创建时间', auto_now=True)

    def __str__(self):
        return '{}'.format(self.money)

    class Meta:
        verbose_name = '充值金额设置'
        verbose_name_plural = verbose_name
        ordering = ["money"]


class RechargeDesc(models.Model):
    desc = models.CharField(verbose_name="充值优惠说明", max_length=1000)
    is_used = models.BooleanField(verbose_name="有效", default=False)
    create_at = models.DateTimeField(verbose_name='创建时间', auto_now=True)

    def __str__(self):
        return self.desc

    class Meta:
        verbose_name = '充值优惠活动说明'
        verbose_name_plural = verbose_name
        ordering = ["-create_at"]


class GiftMoneyRecord(models.Model):
    """
    用户赠送金额记录表
    """
    out_trade_no = models.CharField(verbose_name='订单编号', max_length=32)
    name = models.CharField(verbose_name='用户名', max_length=24, blank=True, default='')
    openid = models.CharField(verbose_name='微信号(openid)', max_length=32)
    transaction_id = models.CharField(verbose_name='微信支付订单号', max_length=32, null=True, blank=True)
    gift_amount = models.DecimalField(verbose_name='赠送金额(元)', default=0, blank=True, max_digits=7, decimal_places=2)
    consume_amount = models.DecimalField(verbose_name='消费额(元)', default=0, blank=True, max_digits=7, decimal_places=2)
    gift_time = models.DateTimeField(verbose_name='赠送时间', blank=True, null=True)
    status = models.BooleanField(verbose_name='是否有效', default=False)
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户赠送金额记录'
        verbose_name_plural = verbose_name
        # ordering = ["add_time"]

    def __str__(self):
        return self.out_trade_no

    def remain_money(self):
        return self.gift_amount - self.consume_amount


class GiftConsumeRecord(models.Model):
    """
    用户赠金使用情况
    """
    out_trade_no = models.CharField(verbose_name='订单编号', max_length=32)
    name = models.CharField(verbose_name='用户名', max_length=24, blank=True, default='')
    openid = models.CharField(verbose_name='微信号(openid)', max_length=32)
    consume_amount = models.DecimalField(verbose_name='消费额(元)', default=0, blank=True, max_digits=7, decimal_places=2)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户赠金使用情况'
        verbose_name_plural = verbose_name
        ordering = ["-add_time"]

    def __str__(self):
        return self.out_trade_no


class UserCollection(models.Model):
    """用户收藏"""
    openid = models.CharField(verbose_name="微信标识", max_length=32, )
    station = models.ForeignKey(Station, verbose_name="充电站", on_delete=models.CASCADE, db_constraint=False)
    create_at = models.DateTimeField(verbose_name="收藏时间", auto_now_add=True)

    def __str__(self):
        return '{}'.format(self.openid)

    class Meta:
        verbose_name = '用户收藏'
        verbose_name_plural = verbose_name


class SubAccount(models.Model):
    """附属账号"""
    sub_user = models.ForeignKey(UserInfo, verbose_name="附属账号", on_delete=models.CASCADE, null=True, db_constraint=False)
    main_user = models.ForeignKey(UserInfo, verbose_name="主账号", related_name="main_users", on_delete=models.CASCADE, null=True, db_constraint=False)
    # recharge_amount = models.DecimalField(verbose_name='充值金额', max_digits=7, decimal_places=2, default=0)
    # balance = models.DecimalField(verbose_name='账户余额', max_digits=7, decimal_places=2, default=0)
    update_time = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    create_time = models.DateTimeField(verbose_name="添加时间", auto_now_add=True)

    def __str__(self):
        return '{}'.format(self.sub_user.nickname)

    class Meta:
        verbose_name = '附属账户'
        verbose_name_plural = verbose_name

    def account_totals(self):
        return self.subaccountconsume_set.all().aggregate(counts=Count("id"), amounts=Sum("consum_money"))


class SubAccountConsume(models.Model):
    """附属账号充值记录"""
    account = models.ForeignKey(SubAccount, verbose_name="附属账号", on_delete=models.CASCADE, null=True, db_constraint=False)
    out_trade_no = models.CharField(verbose_name="订单号", max_length=32, null=True, blank=True)
    charg_pile = models.ForeignKey(ChargingPile, verbose_name="充电桩", on_delete=models.CASCADE, null=True, db_constraint=False)
    gun_num = models.IntegerField(verbose_name="枪口", blank=True, null=True)
    consum_money = models.DecimalField(verbose_name='消费余额(元)', max_digits=7, decimal_places=2, default=0)
    create_time = models.DateTimeField(verbose_name="添加时间", default=datetime.datetime.now)

    def __str__(self):
        return '{}'.format(self.account.sub_user.nickname)

    class Meta:
        verbose_name = '附属账户消费记录'
        verbose_name_plural = verbose_name


class UserBalanceResetRecord(models.Model):
    """用户账号清零记录"""
    name = models.CharField(verbose_name='姓名', max_length=24, blank=True, null=True)
    nickname = models.CharField(verbose_name='昵称', max_length=64, help_text="微信昵称")
    openid = models.CharField(verbose_name='微信ID', max_length=120, blank=True, null=True)
    telephone = models.CharField(verbose_name='手机号码', max_length=18, blank=True, default='')
    total_money = models.DecimalField(verbose_name='充值总额', default=0, blank=True, max_digits=8, decimal_places=2)
    consume_money = models.DecimalField(verbose_name='消费总额', default=0, blank=True, max_digits=8, decimal_places=2)
    binding_amount = models.DecimalField(verbose_name='赠送金额', default=0, blank=True, max_digits=6, decimal_places=2)
    consume_amount = models.DecimalField(verbose_name='赠金消费(元)', default=0, blank=True, max_digits=7, decimal_places=2)
    op_name = models.CharField(verbose_name='操作人', max_length=24, blank=True, null=True)
    oper_time = models.DateTimeField(verbose_name='操作时间', auto_now_add=True)

    def __str__(self):
        return '{}'.format(self.nickname)

    class Meta:
        verbose_name = '账号清零记录'
        verbose_name_plural = verbose_name

