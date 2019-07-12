# coding=utf-8
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


# 运营商管理
from stationmanager.models import Seller, Station


class UserProfile(AbstractUser):
    telephone = models.CharField(max_length=20,verbose_name='手机号', null=True, blank=True)
    seller = models.ForeignKey(Seller, verbose_name='运营商', blank=True, null=True, on_delete=models.SET_NULL)
    station = models.ForeignKey(Station, verbose_name='充电站', blank=True, null=True, on_delete=models.SET_NULL)

# class Profile(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name='用户', blank=True, null=True)
#     seller = models.ForeignKey(Seller, verbose_name='运营商', blank=True, null=True, on_delete=models.SET_NULL)
#     phone_num = models.CharField(max_length=20, null=True, blank=True)
#
#     class Meta:
#         verbose_name = '用户信息'
#         verbose_name_plural = verbose_name
#
#     def __str__(self):
#         return self.phone_num
