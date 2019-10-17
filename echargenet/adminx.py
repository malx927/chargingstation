# coding=utf8

import xadmin

from .models import OperatorInfo, StationInfo, EquipmentInfo, ConnectorInfo, CheckChargeOrder, DisputeOrder


class OperatorInfoAdmin(object):
    """
    运营商信息
    """
    list_display = ["OperatorID", "OperatorName", "OperatorTel1", "OperatorTel2", "OperatorRegAddress", "OperatorNote"]
    search_fields = ["OperatorName"]
    model_icon = 'fa fa-random'
    list_export = ('xls', 'xml', 'json')


xadmin.site.register(OperatorInfo, OperatorInfoAdmin)


class StationInfoAdmin(object):
    list_display = ["StationID", "OperatorID", "EquipmentOwnerID", "StationName", "CountryCode", "AreaCode", "Address"]
    search_fields = ['StationName']
    list_filter = ['OperatorID']
    model_icon = 'fa fa-random'
    relfield_style = 'fk_ajax'


xadmin.site.register(StationInfo, StationInfoAdmin)


class EquipmentInfoAdmin(object):
    """
    充电桩管理
    """
    list_display = ["EquipmentID", "EquipmentName", "StationID",  "EquipmentType", "Power"]
    list_display_links = ["EquipmentID", "EquipmentName"]
    model_icon = 'fa fa-random'


xadmin.site.register(EquipmentInfo, EquipmentInfoAdmin)


class ConnectorInfoAdmin(object):
    list_display = ["ConnectorID", "EquipmentID", "ConnectorName", "ConnectorType", "VoltageUpperLimits", "VoltageLowerLimits",
                    "Current", "Power", "Status"]
    model_icon = 'fa fa-random'


xadmin.site.register(ConnectorInfo, ConnectorInfoAdmin)


class CheckChargeOrderAdmin(object):
    """推送订单核对结果"""
    list_display = ["CheckOrderSeq", "StartTime", "EndTime", "TotalDisputeOrder", "TotalDisputePower", "TotalDisputeMoney"]
    search_fields =["CheckOrderSeq"]
    model_icon = 'fa fa-random'


xadmin.site.register(CheckChargeOrder, CheckChargeOrderAdmin)


class DisputeOrderAdmin(object):
    """单项订单"""
    list_display = ["order", "StartChargeSeq", "TotalPower", "TotalMoney"]
    search_fields =["order__CheckOrderSeq", "StartChargeSeq"]
    model_icon = 'fa fa-random'


xadmin.site.register(DisputeOrder, DisputeOrderAdmin)