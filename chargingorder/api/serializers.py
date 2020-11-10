# -*-coding:utf-8-*-
__author__ = 'malixin'

from rest_framework import serializers

from chargingorder.models import OrderChargDetail


class OrderChargDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderChargDetail
        fields = [
           'out_trade_no', 'current_time', 'voltage', 'current', 'output_voltage', 'output_current'
        ]
