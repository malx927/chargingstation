# -*-coding:utf-8-*-

import datetime
import os
from django.utils import timezone
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework import serializers
from codingmanager.models import AreaCode
from stationmanager.models import ChargingPile, Station, FaultChargingGun

__author__ = 'malixin'


class ChargingPileSerializer(serializers.ModelSerializer):
    piletype = serializers.CharField(source="pile_type.name")
    station_name = serializers.CharField(source="station.name")
    pilemode = SerializerMethodField()
    businessmode = SerializerMethodField()

    class Meta:
        model = ChargingPile
        fields = [
           'id', 'name', 'pile_sn', 'piletype', 'pilemode', 'max_gun', 'fireware', 'get_work_status', 'businessmode', 'station_name',
           'symbol_4g', 'symbol_eth', 'gun_max_voltage', 'gun_min_voltage', 'gun_max_current', 'low_restrict', 'low_offset', 'subscribe_status',
           'faults', 'get_order_url'
        ]

    def get_pilemode(self, obj):
        return obj.get_pile_mode_display() if obj.get_pile_mode_display() is not None else '无'

    def get_businessmode(self, obj):
        return obj.get_business_mode_display() if obj.get_business_mode_display() is not None else '无'


class AreaCodeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AreaCode
        fields = [
            'code',
            'name',
        ]


class StationSerializer(serializers.ModelSerializer):
    gun_stats = SerializerMethodField()
    detail_address = SerializerMethodField()
    image_url = SerializerMethodField()

    class Meta:
        model = Station
        fields = [
            'name', 'province', 'city', 'district', 'address',  'longitude', 'latitude',
            'seller', 'telephone', "gun_stats", "detail_address", "image_url", "get_absolute_url"
        ]

    def get_gun_stats(self, obj):
        return obj.get_gun_totals()

    def get_detail_address(self, obj):
        return obj.get_detail_address()

    def get_image_url(self, obj):
        station_image = obj.stationimage_set.first()
        if station_image:
            return station_image.image.url
        else:
            return ""

