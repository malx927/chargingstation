# -*-coding:utf-8-*-

import datetime
import os
from django.utils import timezone

from chargingorder.models import Order
from echargenet.models import OperatorInfo, StationInfo, EquipmentInfo, ConnectorInfo
from rest_framework.fields import SerializerMethodField
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework import serializers
__author__ = 'malixin'


class ConnectorInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorInfo
        fields = ["ConnectorID",  "EquipmentID", "ConnectorType", "VoltageUpperLimits",
                  "VoltageLowerLimits", "Current", "Power", 'NationalStandard']


class EquipmentInfoSerializer(serializers.ModelSerializer):
    ConnectorInfos = ConnectorInfoSerializer(many=True, read_only=True)

    class Meta:
        model = EquipmentInfo
        fields = ["EquipmentID", "ManufacturerID", "EquipmentModel", "ProductionDate", "ProductionDate", "EquipmentType",
                  "Power", "EquipmentName", "ConnectorInfos"]


class StationInfoSerializer(serializers.ModelSerializer):
    EquipmentInfos = serializers.SerializerMethodField()
    OperatorID = serializers.SerializerMethodField()

    class Meta:
        model = StationInfo
        fields = ["OperatorID", "StationID", "StationName", "EquipmentOwnerID", "CountryCode", "AreaCode", "Address",
                  "ServiceTel", "StationType", "StationStatus", "ParkNums", "StationLng", "StationLat", "Construction",
                  "EquipmentInfos"]

    def get_OperatorID(self, obj):
        return obj.OperatorID.OperatorID

    def get_EquipmentInfos(self, obj):
        equip_infos = EquipmentInfo.objects.filter(StationID__StationID=obj.StationID, is_subsidy=1)        # 运营补贴
        serializer = EquipmentInfoSerializer(equip_infos, many=True)
        return serializer.data


class OperatorInfoSerializer(serializers.ModelSerializer):
    StationInfos = StationInfoSerializer(many=True, read_only=True)

    class Meta:
        model = OperatorInfo
        fields = ["OperatorID", "StationInfos"]


class ConnectorStatusInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorInfo
        fields = ["ConnectorID", "Status"]


class StationStatusInfoSerializer(serializers.ModelSerializer):
    ConnectorStatusInfos = serializers.SerializerMethodField()

    class Meta:
        model = StationInfo
        fields = ["StationID", "ConnectorStatusInfos"]

    def get_ConnectorStatusInfos(self, obj):
        Connectors = ConnectorInfo.objects.filter(EquipmentID__StationID__StationID=obj.StationID)
        serializer = ConnectorStatusInfoSerializer(Connectors, many=True)
        return serializer.data


# # 充电设备接口统计信息
# class ConnectorStatsInfoSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = Order
#         fields = ["StationID", "ConnectorStatusInfos"]