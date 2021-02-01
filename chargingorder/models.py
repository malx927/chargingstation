# coding=utf8
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import models
from codingmanager.constants import *
from codingmanager.models import FaultCode
from django.urls import reverse
from stationmanager.models import ChargingPile, Seller, Station
from django.db.models.signals import post_save
from django.dispatch import receiver
from wxchat.models import UserInfo


class Order(models.Model):
    """
    充电订单
    """
    RESULT = (
        (0, '上报'),
        (None,  '空'),
    )
    out_trade_no = models.CharField(verbose_name='订单编号', max_length=32, db_index=True)  # 电桩编号 + YYYYMMDD + random
    openid = models.CharField(verbose_name='用户ID(openid)', max_length=64, blank=True, null=True,)
    name = models.CharField(verbose_name='姓名(或昵称)', max_length=64, blank=True, null=True,)
    seller = models.ForeignKey(Seller, verbose_name='运营商', blank=True, null=True, on_delete=models.SET_NULL, db_constraint=False)
    station = models.ForeignKey(Station, verbose_name='充电站', blank=True, null=True, on_delete=models.SET_NULL, db_constraint=False)
    charg_pile = models.ForeignKey(ChargingPile, verbose_name='充电桩', blank=True, null=True, on_delete=models.SET_NULL, db_constraint=False)
    gun_num = models.CharField(verbose_name='枪口号', max_length=12, blank=True, null=True,)
    protocol = models.IntegerField(verbose_name='充电国标协议', choices=INTER_PROTOCAL, blank=True, null=True)
    start_model = models.IntegerField(verbose_name='启动方式', choices=STARTUP_MODEL, default=0)
    charg_mode = models.IntegerField(verbose_name='充电类型', choices=USER_CHARGING_MODE, blank=True, default=0)
    charg_type = models.IntegerField(verbose_name='设备充电模式', choices=PILE_CHARGING_MODE, blank=True, default=0)
    charg_status = models.ForeignKey(FaultCode, verbose_name='充电状态', blank=True, null=True, on_delete=models.SET_NULL, db_constraint=False)
    begin_soc = models.DecimalField(verbose_name='初始SOC', blank=True, default=0, max_digits=6, decimal_places=2)
    end_soc = models.DecimalField(verbose_name='结束SOC', blank=True, default=0, max_digits=6, decimal_places=2)
    begin_time = models.DateTimeField(verbose_name='开始时间', blank=True, null=True)
    end_time = models.DateTimeField(verbose_name='结束时间', blank=True, null=True)
    begin_reading = models.DecimalField(verbose_name='初始电表数', blank=True, default=0, max_digits=9, decimal_places=2)
    end_reading = models.DecimalField(verbose_name='结束电表数', blank=True, default=0, max_digits=9, decimal_places=2)
    total_readings = models.DecimalField(verbose_name='充电量(KWH)', blank=True, default=0, max_digits=9, decimal_places=2)
    prev_reading = models.DecimalField(verbose_name='上次电表读数', blank=True, default=0, max_digits=9, decimal_places=2)
    # 按分钟，SOC， 电量支付
    charg_min_val = models.IntegerField(verbose_name='按分钟充电', blank=True, default=0)   # 按分钟充电取此值判断
    charg_soc_val = models.IntegerField(verbose_name='按SOC充电', blank=True, default=0)   # 按SOC充电取此值判断
    charg_reading_val = models.IntegerField(verbose_name='按电量充电', blank=True, default=0)   # 按电量充电取此值判断
    # 微信支付
    total_fee = models.DecimalField(verbose_name='充值金额(元)',  max_digits=10, decimal_places=2, blank=True, default=0)
    cash_fee = models.DecimalField(verbose_name='实付金额(元)',  max_digits=10, decimal_places=2, blank=True, default=0)
    pay_time = models.DateTimeField(verbose_name='支付时间', blank=True, null=True)
    transaction_id = models.CharField(verbose_name='微信订单号', max_length=32, null=True, blank=True)
    consum_money = models.DecimalField(verbose_name='消费总金额',  max_digits=10, decimal_places=2, blank=True, default=0)
    # 车辆信息
    car_type = models.CharField(verbose_name="车型", max_length=32, blank=True, null=True)
    vin_code = models.CharField(verbose_name='车辆VIN码', max_length=32, blank=True, null=True,)
    max_current = models.IntegerField(verbose_name='车辆最高充电电流', blank=True, null=True)
    max_voltage = models.IntegerField(verbose_name='车辆最高充电电压',  blank=True, null=True)
    max_single_voltage = models.IntegerField(verbose_name='车辆最高单体电池电压',  blank=True, null=True)
    max_temp = models.IntegerField(verbose_name='车辆最高充电温度', blank=True, null=True)
    power_fee = models.DecimalField(verbose_name='电费(元)', blank=True, default=0, max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(verbose_name='服务费(元)', blank=True, default=0, max_digits=10, decimal_places=2)
    park_fee = models.DecimalField(verbose_name='停车费', blank=True, default=0, max_digits=6, decimal_places=2)
    status = models.IntegerField(verbose_name='订单状态', choices=ORDER_STATUS, default=0)
    main_openid = models.CharField(verbose_name='主账号ID', max_length=64, blank=True, null=True,)
    balance = models.DecimalField(verbose_name='余额(元)', blank=True, default=0, max_digits=8, decimal_places=2)
    start_charge_seq = models.CharField(verbose_name='e充电订单号', max_length=32, blank=True, null=True,)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    report_result = models.IntegerField(verbose_name='上报确认', blank=True, null=True, choices=RESULT)
    report_time = models.DateTimeField(verbose_name='上报确认时间', blank=True, null=True)
    output_voltage = models.FloatField(verbose_name='输出电压(V)', blank=True, default=0)
    output_current = models.FloatField(verbose_name='输出电流(A)', blank=True, default=0)

    def __str__(self):
        return self.out_trade_no

    class Meta:
        verbose_name = '充电订单'
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]

    # 充电时间
    def total_minutes(self):
        if self.end_time and self.begin_time:
            mins = Decimal((self.end_time - self.begin_time).total_seconds()/60)
            return mins.quantize(Decimal('0.01'))
        else:
            return 0
    total_minutes.short_description = '充电时长(min)'

    def power(self):
        return self.output_current * self.output_voltage / 1000

    def total_seconds(self):
        if self.end_time and self.begin_time:
            seconds = (self.end_time - self.begin_time).total_seconds()
            return seconds
        else:
            return 0

    def total_hours(self):
        if self.end_time and self.begin_time:
            hours = Decimal((self.end_time - self.begin_time).total_seconds()/3600)
            return hours.quantize(Decimal('0.01'))
        else:
            return 0

    # 充电总量
    def get_total_reading(self):
        if self.end_reading == 0:
            return 0
        return (self.end_reading - self.begin_reading).quantize(Decimal("0.01"))
    get_total_reading.short_description = '充电总量'

    def get_record(self):
        return OrderRecord.objects.filter(out_trade_no=self.out_trade_no).first()
        # return self.records.all().first()

    def get_balance(self):
        return self.balance - self.consum_money

    def get_work_status(self):
        gun = self.charg_pile.charginggun_set.filter(gun_num=self.gun_num).first()
        if gun:
            return gun.get_work_status_display()
        else:
            return ""

    def get_absolute_url(self):
        return reverse("user-order-detail", kwargs={"pk": self.id})

    # def car_type(self):
    #     user = UserInfo.objects.filter(openid=self.openid).first()
    #     if user and user.car_type:
    #         return user.car_type
    #     return ""
    #
    # car_type.short_description = '车型'


# @receiver(post_save, sender=Order)
# def send_cmd(sender, instance, created, **kwargs):
#     print(created, instance, 'order signal')


class ChargingOrder(Order):
    """充电中的订单"""
    class Meta:
        proxy = True
        verbose_name = '充电中订单'
        verbose_name_plural = verbose_name


class UnusualOrder(Order):
    """异常订单"""
    class Meta:
        proxy = True
        verbose_name = '异常订单'
        verbose_name_plural = verbose_name


class OrderRecord(models.Model):
    """
    充值记录表
    """
    serial_num = models.CharField(verbose_name='流水号', max_length=24, blank=True, null=True,) #YYYYMMDDHHMiSS
    order = models.ForeignKey(Order, verbose_name='订单', related_name='records', blank=True, null=True, on_delete=models.SET_NULL, db_constraint=False)
    station_id = models.IntegerField(verbose_name='电桩ID', blank=True, null=True)
    seller_id = models.IntegerField(verbose_name='运营商ID', blank=True, null=True)
    pile_sn = models.CharField(verbose_name="电桩编码SN", max_length=32, blank=True, null=True)
    gun_num = models.CharField(verbose_name='枪口号', max_length=12, blank=True, null=True,)
    out_trade_no = models.CharField(verbose_name='订单号', max_length=32, blank=True, null=True, db_index=True)
    begin_time = models.DateTimeField(verbose_name='起始时间', blank=True, null=True)
    end_time = models.DateTimeField(verbose_name='截止时间', blank=True, null=True)
    current_soc = models.IntegerField(verbose_name="当前SOC", blank=True, default=0)
    begin_reading = models.DecimalField(verbose_name='起始电表数', blank=True, default=0, max_digits=9, decimal_places=2)
    end_reading = models.DecimalField(verbose_name='截止电表数', blank=True, default=0, max_digits=9, decimal_places=2)
    price = models.DecimalField(verbose_name='电费电价', max_digits=5, decimal_places=2, blank=True, default=0)
    service_price = models.DecimalField(verbose_name='服务费价格', max_digits=5, decimal_places=2, blank=True, default=0)
    price_begin_time = models.TimeField(verbose_name='价格起始时间', blank=True, null=True)
    price_end_time = models.TimeField(verbose_name='价格截止时间', blank=True, null=True)
    accumulated_readings = models.DecimalField(verbose_name='累计充电量', blank=True, default=0, max_digits=9, decimal_places=2)
    accumulated_amount = models.DecimalField(verbose_name='累计电费', blank=True, default=0, max_digits=9, decimal_places=2)
    accumulated_service_amount = models.DecimalField(verbose_name='累计服务费', blank=True, default=0, max_digits=9, decimal_places=2)
    update_time = models.DateTimeField(verbose_name='添加时间', auto_now=True)

    def __str__(self):
        return self.serial_num

    class Meta:
        verbose_name = '订单明细'
        verbose_name_plural = verbose_name
        ordering = ["-update_time"]

    def charging_time(self):
        return (self.end_time - self.begin_time).seconds
    charging_time.short_description = '充电时间(秒)'

    def meter_quantity(self):
        return self.end_reading - self.begin_reading
    meter_quantity.short_description = '充电电量(度)'

    def power_money(self):
        return (self.end_reading - self.begin_reading) * self.price
    power_money.short_description = '电费金额(元)'

    def service_money(self):
        return (self.end_reading - self.begin_reading) * self.service_price
    service_money.short_description = '服务费金额(元)'


class OrderChargDetail(models.Model):
    """
    充电监控明细
    """
    pile_sn = models.CharField(verbose_name="电桩SN", max_length=32, blank=True, null=True)
    gun_num = models.IntegerField(verbose_name="枪口", blank=True, null=True)
    out_trade_no = models.CharField(verbose_name="订单编号", max_length=32, blank=True, null=True)
    current_time = models.DateTimeField(verbose_name='当前时间', blank=True, null=True)
    current_soc = models.IntegerField(verbose_name="当前SOC", blank=True, default=0)
    voltage = models.IntegerField(verbose_name='所需电压值', blank=True, default=0)
    current = models.IntegerField(verbose_name='所需电流值', blank=True, default=0)
    output_voltage = models.FloatField(verbose_name='实际输出电压值', blank=True, default=0)
    output_current = models.FloatField(verbose_name='实际输出电流', blank=True, default=0)
    gun_temp = models.DecimalField(verbose_name='枪头温度1', blank=True, null=True, max_digits=6, decimal_places=2)
    gun_temp1 = models.DecimalField(verbose_name='枪头温度2', blank=True, null=True, max_digits=6, decimal_places=2)
    cab_temp = models.DecimalField(verbose_name='柜内温度1', blank=True, null=True, max_digits=6, decimal_places=2)
    cab_temp1 = models.DecimalField(verbose_name='柜内温度2', blank=True, null=True, max_digits=6, decimal_places=2)
    current_reading = models.DecimalField(verbose_name='当前电表数', blank=True, default=0, max_digits=9, decimal_places=2)
    prev_reading = models.DecimalField(verbose_name='上次电表数', blank=True, default=0, max_digits=9, decimal_places=2)
    update_time = models.DateTimeField(verbose_name='添加时间', auto_now=True)

    def __str__(self):
        return self.out_trade_no

    class Meta:
        verbose_name = '充电监控'
        verbose_name_plural = verbose_name
        ordering = ["-current_time"]


class GroupName(models.Model):
    name = models.CharField(verbose_name='组名', max_length=64)
    channel_name = models.CharField(verbose_name='频道ID', max_length=64)
    nums = models.IntegerField(verbose_name='连接数量', default=0)
    create_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "工作组"
        verbose_name_plural = verbose_name


class ChargingCmdRecord(models.Model):
    pile_sn = models.CharField(verbose_name="电桩SN", max_length=32, blank=True, null=True)
    gun_num = models.IntegerField(verbose_name="枪口号", blank=True, null=True)
    out_trade_no = models.CharField(verbose_name="订单编号", max_length=32, blank=True, null=True)
    send_cmd = models.CharField(verbose_name="发送命令", max_length=1024, blank=True, null=True)
    send_time = models.DateTimeField(verbose_name="发送时间", auto_now=True)
    over_time = models.DateTimeField(verbose_name="超时时间", blank=True, null=True)
    send_count = models.IntegerField(verbose_name="发送次数", default=0)
    cmd_flag = models.CharField(verbose_name="标志", max_length=10, blank=True, null=True)
    add_time = models.DateTimeField(verbose_name="添加时间", auto_now_add=True)

    def __str__(self):
        return self.out_trade_no

    class Meta:
        verbose_name = "充电命令超时记录"
        verbose_name_plural = verbose_name


class ChargingStatusRecord(models.Model):
    """充电状态记录表"""
    pile_sn = models.CharField(verbose_name="充电桩SN", max_length=32)
    gun_num = models.IntegerField(verbose_name="枪口号")
    pile_type = models.IntegerField(verbose_name="电桩类型", default=0)
    out_trade_no = models.CharField(verbose_name="订单号", max_length=32)
    recv_time = models.DateTimeField(verbose_name="接收时间", auto_now=True)
    over_time = models.DateTimeField(verbose_name="超时时间", blank=True, null=True)
    add_time = models.DateTimeField(verbose_name="添加时间", auto_now_add=True)

    def __str__(self):
        return self.pile_sn

    class Meta:
        verbose_name = "充电状态记录表"
        verbose_name_plural = verbose_name


class Track(models.Model):
    """用户充电轨迹"""
    out_trade_no = models.CharField(verbose_name='订单编号', max_length=32, blank=True, null=True)
    oper_name = models.CharField(verbose_name='执行操作', max_length=32, blank=True, null=True)
    oper_user = models.CharField(verbose_name='执行者', max_length=32, blank=True, null=True)
    oper_time = models.DateTimeField(verbose_name='执行时间', blank=True, null=True)
    comments = models.CharField(verbose_name='备注', max_length=512, blank=True, null=True)

    def __str__(self):
        return self.oper_name

    class Meta:
        verbose_name = "用户充电轨迹"
        verbose_name_plural = verbose_name
