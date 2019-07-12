# coding=utf-8
import binascii
import datetime
import os

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from codingmanager.constants import STATION_TYPES, STATION_STATUS, STATION_PLACE, NATIONAL_STANDARD, CONNECTOR_TYPE
from django.utils import timezone


class OperatorInfo(models.Model):
    """
    设备运营商信息
    """
    ID = models.IntegerField(verbose_name='ID', primary_key=True)
    OperatorID = models.CharField(verbose_name='运营商ID', max_length=9)
    OperatorName = models.CharField(verbose_name='运营商名称', max_length=64)
    OperatorTel1 = models.CharField(verbose_name='运营商电话1', max_length=32)
    OperatorTel2 = models.CharField(verbose_name='运营商电话2 ', max_length=32, blank=True, null=True)
    OperatorRegAddress = models.CharField(verbose_name='运营商注册地址', max_length=64, blank=True, null=True)
    OperatorNote = models.CharField(verbose_name='备注', max_length=255, blank=True, null=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now=True)

    class Meta:
        verbose_name = '设备运营商信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.OperatorName


class StationInfo(models.Model):
    """
    充电站信息
    """
    StationID = models.CharField(verbose_name='充电站ID', max_length=20,  primary_key=True)
    OperatorID = models.ForeignKey(OperatorInfo, verbose_name='运营商ID', null=True, on_delete=models.SET_NULL)
    EquipmentOwnerID = models.CharField(verbose_name='设备所属方ID', max_length=9)
    StationName = models.CharField(verbose_name='充电站名称', max_length=50)
    CountryCode = models.CharField(verbose_name='国家代码', max_length=2, default='CN')
    AreaCode = models.CharField(verbose_name='省市辖区编码 ', max_length=20)
    Address = models.CharField(verbose_name='详细地址', max_length=50)
    StationTel = models.CharField(verbose_name='站点电话', max_length=30, blank=True, null=True)
    ServiceTel = models.CharField(verbose_name='服务电话', max_length=30, default='')
    StationType = models.IntegerField(verbose_name='站点类型', choices=STATION_TYPES)
    StationStatus = models.IntegerField(verbose_name='站点状态',  choices=STATION_STATUS)
    ParkNums = models.IntegerField(verbose_name='车位数量', default=0)
    StationLng = models.DecimalField(verbose_name='经度', default=0, decimal_places=6, max_digits=12)
    StationLat = models.DecimalField(verbose_name='纬度', default=0, decimal_places=6, max_digits=12)
    SiteGuide = models.CharField(verbose_name='站点引导', max_length=100, blank=True, null=True)
    Construction = models.IntegerField(verbose_name='建设场所', choices=STATION_PLACE)
    MatchCars = models.CharField(verbose_name='使用车型描述', max_length=100, blank=True, null=True)
    ParkInfo = models.CharField(verbose_name='车位楼层及数量描述', max_length=100, blank=True, null=True)
    BusineHours = models.CharField(verbose_name='营业时间', max_length=100, blank=True, null=True)
    ElectricityFee = models.CharField(verbose_name='充电电费率', max_length=256, blank=True, null=True)
    ServiceFee = models.CharField(verbose_name='服务费率', max_length=100, blank=True, null=True)
    ParkFee = models.CharField(verbose_name='停车费', max_length=100, blank=True, null=True)
    Payment = models.CharField(verbose_name='支付方式', max_length=20, blank=True, null=True)
    SupportOrder = models.IntegerField(verbose_name='是否支持预约', blank=True, null=True)
    Remark = models.CharField(verbose_name='备注', max_length=100, blank=True, null=True)
    add_time = models.DateTimeField(verbose_name="添加时间", auto_now=True)

    class Meta:
        verbose_name = '充电站信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.StationName


class EquipmentInfo(models.Model):
    """
    充电设备信息
    """
    EQUIP_TYPE = (
        (1, '直流设备'),
        (2, '交流设备'),
        (3, '交直流一体设备'),
        (4, '无线设备'),
        (5, '其他'),
    )
    EquipmentID = models.CharField(verbose_name='设备编码', max_length=23,  primary_key=True)
    StationID = models.ForeignKey(StationInfo, verbose_name='充电站', related_name="EquipmentInfos")
    ManufacturerID = models.CharField(verbose_name='生产商组织机构代码', max_length=9, blank=True, default="")
    ManufacturerName = models.CharField(verbose_name='设备生产商名称', max_length=30,  blank=True, default="")
    EquipmentModel = models.CharField(verbose_name='设备型号', max_length=20, blank=True, default="")
    ProductionDate = models.CharField(verbose_name='设备生产日期', max_length=10,  blank=True, default="")
    EquipmentType = models.IntegerField(verbose_name='设备类型', choices=EQUIP_TYPE)
    EquipmentLng = models.FloatField(verbose_name='经度', default=0)
    EquipmentLat = models.FloatField(verbose_name='纬度', default=0)
    Power = models.DecimalField(verbose_name='设备总功率', max_digits=7, decimal_places=1)
    EquipmentName = models.CharField(verbose_name='充电设备名称', max_length=30, blank=True, default="")
    is_subsidy = models.IntegerField(verbose_name='运营补贴', default=0, choices=((0, '否'), (1, '运营补贴')))
    add_time = models.DateTimeField(verbose_name="添加时间", auto_now=True)

    class Meta:
        verbose_name = '充电设备信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        if self.EquipmentName:
            return self.EquipmentName
        else:
            return self.EquipmentID


# 充电设备接口信息
class ConnectorInfo(models.Model):
    """
    充电设备接口信息
    """
    CONNECTOR_STATUS = (
        (0, '离网'),
        (1, '空闲'),
        (2, '占用(未充电)'),
        (3, '占用(充电中)'),
        (4, '占用(预约锁定)'),
        (255, '故障'),
    )
    PARK_STATUS = (
        (0, '未知'),
        (10, '空闲'),
        (50, '占用'),
    )
    LOCK_STATUS = (
        (0, '未知'),
        (10, '已解锁'),
        (50, '已上锁'),
    )
    ID = models.IntegerField(verbose_name='ID', primary_key=True)
    ConnectorID = models.CharField(verbose_name='充电设备接口编码', max_length=26)
    EquipmentID = models.ForeignKey(EquipmentInfo, verbose_name='充电设备', related_name="ConnectorInfos")
    ConnectorName = models.CharField(verbose_name='充电设备接口名称', max_length=30, blank=True, null=True)
    ConnectorType = models.IntegerField(verbose_name='接口类型', choices=CONNECTOR_TYPE)
    VoltageUpperLimits = models.IntegerField(verbose_name='额定电压上限')
    VoltageLowerLimits = models.IntegerField(verbose_name='额定电压下限')
    Current = models.IntegerField(verbose_name='额定电流')
    Power = models.DecimalField(verbose_name='额定功率', max_digits=6, decimal_places=1)
    ParkNo = models.CharField(verbose_name='车位号',  max_length=10, blank=True, null=True)
    NationalStandard = models.IntegerField(verbose_name='国家标准', choices=NATIONAL_STANDARD)
    Status = models.IntegerField(verbose_name='设备接口状态', choices=CONNECTOR_STATUS)
    ParkStatus = models.IntegerField(verbose_name='车位状态', choices=PARK_STATUS, blank=True, null=True)
    LockStatus = models.IntegerField(verbose_name='地锁状态', choices=LOCK_STATUS, blank=True, null=True)
    add_time = models.DateTimeField(verbose_name="添加时间", auto_now=True)

    class Meta:
        verbose_name = '充电设备接口信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.ConnectorID


class CheckChargeOrder(models.Model):
    """推送订单核对结果"""
    CheckOrderSeq = models.CharField(verbose_name='订单对账流水号', max_length=27)
    StartTime = models.DateTimeField(verbose_name='订单开始时间')
    EndTime = models.DateTimeField(verbose_name='订单结束时间')
    TotalDisputeOrder = models.IntegerField(verbose_name='争议订单数量')
    TotalDisputePower = models.DecimalField(verbose_name='总电量(度)', max_digits=9, decimal_places=4, blank=True, null=True)
    TotalDisputeMoney = models.DecimalField(verbose_name='总金额(元)', max_digits=9, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = '推送订单核对结果'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.CheckOrderSeq


class DisputeOrder(models.Model):
    """单项订单"""
    order = models.ForeignKey(CheckChargeOrder, verbose_name='争议订单')
    StartChargeSeq = models.CharField(verbose_name='充电订单号', max_length=27)
    TotalPower = models.DecimalField(verbose_name='累计充电量(度)', max_digits=9, decimal_places=2, blank=True, null=True)
    TotalMoney = models.DecimalField(verbose_name='累计总金额(元)', max_digits=9, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = '争议交易单项订单'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.StartChargeSeq


class Token(models.Model):
    """
    The default authorization token model.
    """
    OperatorID = models.CharField(verbose_name="运营商标识", max_length=12)
    OperatorSecret = models.CharField(verbose_name="运营商密钥", max_length=32)
    key = models.CharField(verbose_name="令牌", max_length=40)
    expire_at = models.DateTimeField(verbose_name="过期时间",)
    created = models.DateTimeField(verbose_name="创建时间", default=timezone.now)

    class Meta:
        verbose_name = "用户令牌"
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode().upper()