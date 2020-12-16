# coding=utf8
from django.db import models


# 充电桩类型 电桩类型(D7-D5)
class PileType(models.Model):
    id = models.IntegerField(verbose_name='编码', primary_key=True, default=0)
    name = models.CharField(verbose_name='类型', max_length=32)
    remark = models.CharField(verbose_name='说明', max_length=64, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '电桩类型'
        verbose_name_plural = verbose_name
        ordering = ['id']


# 故障原因编码
class FaultCode(models.Model):
    STATUS = (
        (0, '无'),
        (1, '故障'),
    )
    id = models.IntegerField(verbose_name='故障编码', primary_key=True, default=0)
    name = models.CharField(verbose_name='故障原因', max_length=32)
    fault = models.IntegerField(verbose_name="故障标识", choices=STATUS, default=0)
    remark = models.CharField(verbose_name='说明', max_length=64, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '故障原因编码'
        verbose_name_plural = verbose_name
        ordering = ['id']


class ChargeStatusManager(models.Manager):
    def get_queryset(self):
        return super(ChargeStatusManager, self).get_queryset().filter(pk__lte=10)


# 充电状态编码
class ChargeStatusCode(FaultCode):
    objects = ChargeStatusManager()

    class Meta:
        proxy = True
        verbose_name = '充电状态编码'
        verbose_name_plural = verbose_name


class PriceType(models.Model):
    """
    充电收费类型(电站自有/运营公司/集团大客户)
    """
    name = models.CharField(verbose_name='类型名称', max_length=32)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '收费类型'
        verbose_name_plural = verbose_name


class AreaCode(models.Model):
    """
    地区编码
    """
    code = models.CharField(verbose_name=u'地区编码', primary_key=True, max_length=18)
    name = models.CharField(verbose_name=u'地区名称', max_length=50)

    class Meta:
        verbose_name=u'地区编码表'
        verbose_name_plural = verbose_name
        ordering = ['code']

    def __str__(self):
        return self.name