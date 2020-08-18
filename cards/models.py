from chargingorder.models import Order
from django.db import models
from django.utils.safestring import mark_safe

from chargingstation import settings
from stationmanager.models import Station, Seller


# class CardUser(models.Model):
#     """储值卡用户"""
#     name = models.CharField(verbose_name="用户名称", max_length=64, unique=True)
#     password = models.CharField(verbose_name="登录密码", max_length=128)
#     telephone = models.CharField(verbose_name="联系电话", max_length=64)
#     address = models.CharField(verbose_name="详细地址", max_length=240, blank=True, null=True)
#     bank = models.CharField(verbose_name="开户行", max_length=64, blank=True, null=True)
#     account = models.CharField(verbose_name="银行账号", max_length=64, blank=True, null=True)
#     is_active = models.IntegerField(verbose_name="是否有效", choices=((1, "有效"), (0, "禁用")), default=1)
#     last_login = models.DateTimeField(verbose_name='最近登录时间', default=timezone.now)
#     update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
#     add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)
#
#     def __str__(self):
#         return self.name
#
#     class Meta:
#         verbose_name = '储值卡用户'
#         verbose_name_plural = verbose_name


class ChargingCard(models.Model):
    """储值卡"""
    STATUS = (
        (1, "启用"),
        (0, "禁用"),
    )
    VALID_STATUS =(
        (0, '无'),
        (1, '设置'),
    )
    card_num = models.CharField(verbose_name="卡号", max_length=128, unique=True)
    cipher = models.CharField(verbose_name="卡密钥", max_length=128, default='123456')
    name = models.CharField(verbose_name='用户名', max_length=32, blank=True, null=True)
    telephone = models.CharField(verbose_name="电话号码", max_length=18)
    seller = models.ForeignKey(Seller, verbose_name="运营商", on_delete=models.SET_NULL, blank=True, null=True, db_constraint=False)
    station = models.ManyToManyField(Station, verbose_name='充电站', blank=True, db_constraint=False)
    sec_num = models.CharField(verbose_name="备用卡号", max_length=128, blank=True, null=True)
    money = models.DecimalField(verbose_name="余额", default=0, max_digits=10, decimal_places=2)
    status = models.IntegerField(verbose_name="状态", choices=STATUS, default=1)
    is_valid_date = models.BooleanField(verbose_name='设置有效期', default=0, choices=VALID_STATUS)
    start_date = models.DateField(verbose_name="生效开始时间", blank=True, null=True)
    end_date = models.DateField(verbose_name="生效结束时间", blank=True, null=True)
    pile_sn = models.CharField(verbose_name='电桩SN', max_length=64, blank=True, null=True)
    gun_num = models.CharField(verbose_name='枪口号', max_length=12, blank=True, null=True)
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    def __str__(self):
        return self.card_num

    class Meta:
        verbose_name = '储值卡'
        verbose_name_plural = verbose_name

    # def stations(self):
    #     station_list = []
    #     for station in self.station.all():
    #         station_list.append(station.name)
    #
    #     if station_list:
    #         return "\".join(station_list)
    #     else:
    #         return '空'

    # stations.short_description = '充电站'

    def startup(self):
        start_url = "/cards/cards_startup/?c_id={}&status={}".format(self.id, 1)
        stop_url = "/cards/cards_startup/?c_id={}&status={}".format(self.id, 0)
        charging_url = "/cards/recharge_money/?c_id={}".format(self.id)
        startup = " <a class='btn btn-xs btn-default' href='{}'>启用</a> ".format(start_url)
        stop = " <a class='btn btn-xs btn-danger' href='{}'>禁用</a> ".format(stop_url)
        charging = " <a class='btn btn-xs btn-success' data-toggle='modal' data-target='#myModal' data-uri='{}'>充值</a>".format(charging_url)
        return mark_safe(startup + stop + charging)

    startup.short_description = "选项"


class CardRecharge(models.Model):
    """充值记录表"""
    card = models.CharField(verbose_name="储蓄卡", max_length=128)
    seller = models.ForeignKey(Seller, verbose_name="运营商", on_delete=models.SET_NULL, blank=True, null=True, db_constraint=False)
    money = models.IntegerField(verbose_name="充值金额(元)", default=0)
    op_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='操作人', blank=True, null=True, db_constraint=False)
    add_time = models.DateTimeField(verbose_name="充值时间", auto_now_add=True)

    def __str__(self):
        return self.card

    class Meta:
        verbose_name = '储值卡充值记录'
        verbose_name_plural = verbose_name


class CardOrder(Order):
    """储值卡消费记录"""
    class Meta:
        proxy = True
        verbose_name = '储值卡消费记录'
        verbose_name_plural = verbose_name