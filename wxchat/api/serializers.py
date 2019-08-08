# -*-coding:utf-8-*-

import datetime
import os
from django.utils import timezone
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework import serializers
from codingmanager.models import AreaCode
from stationmanager.models import ChargingPile
from wxchat.models import UserInfo, UserCollection

__author__ = 'malixin'


# 宠物丢失
class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        fields = ['id', 'openid', 'name', 'user_type', 'account_balance']


class UserCollectonSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCollection
        fields = ["id", "openid", "station"]
