from django.db import models


class CardUser(models.Model):
    """储值卡用户"""
    name = models.CharField(verbose_name="用户名称", max_length=64)
    password = models.CharField(verbose_name="登录密码", max_length=128)
    telephone = models.CharField(verbose_name="联系电话", max_length=64)
    address = models.CharField(verbose_name="详细地址", max_length=240, blank=True, null=True)
    bank = models.CharField(verbose_name="开户行", max_length=64, blank=True, null=True)
    account = models.CharField(verbose_name="银行账号", max_length=64, blank=True, null=True)
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '储值卡用户'
        verbose_name_plural = verbose_name


class ChargingCard(models.Model):
    """储值卡"""
    STATUS = (
        (1, "启用"),
        (0, "禁用"),
    )
    card_num = models.CharField(verbose_name="卡号", max_length=128)
    cipher = models.CharField(verbose_name="卡密钥", max_length=128)
    sec_num = models.CharField(verbose_name="备用卡号", max_length=128, blank=True, null=True)
    user = models.ForeignKey(CardUser, verbose_name="用户", blank=True, null=True, on_delete=models.SET_NULL)
    money = models.DecimalField(verbose_name="余额", default=0, max_digits=10, decimal_places=2)
    status = models.IntegerField(verbose_name="状态", choices=STATUS, default=0)
    start_date = models.DateField(verbose_name="生效开始时间")
    end_date = models.DateField(verbose_name="生效结束时间")
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    def __str__(self):
        return self.card_num

    class Meta:
        verbose_name = '储值卡'
        verbose_name_plural = verbose_name