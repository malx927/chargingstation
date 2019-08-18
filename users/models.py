# coding=utf-8
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


# 运营商管理
from stationmanager.models import Seller, Station
from wxchat.models import GroupClients, UserInfo


class UserProfile(AbstractUser):
    telephone = models.CharField(max_length=20, verbose_name='手机号', null=True, blank=True)
    seller = models.ForeignKey(Seller, verbose_name='运营商', blank=True, null=True, on_delete=models.SET_NULL)
    station = models.ForeignKey(Station, verbose_name='充电站', blank=True, null=True, on_delete=models.SET_NULL)
    groups_client = models.ForeignKey(GroupClients, verbose_name='集团客户名称', blank=True, null=True, on_delete=models.SET_NULL)
    wx_user = models.ForeignKey(UserInfo, verbose_name="微信用户", blank=True, null=True, on_delete=models.SET_NULL)
