# coding=utf8
from codingmanager.models import *
import xadmin

# Register your models here.


# 电桩类型
class PileTypeAdmin(object):
    list_display = ['id', 'name', 'remark']
    list_display_links = ['name', 'id']
    search_fields = ['name']
    model_icon = 'fa fa-star'


# # 充电桩实时状态
# class RealTimeStatusAdmin(object):
#     list_display = ['id', 'name', 'remark']
#     search_fields = ['name']
#     model_icon = 'fa fa-clock-o'
#

# 故障原因编码
class FaultCodeAdmin(object):
    list_display = ['id', 'name', 'fault', 'remark']
    list_display_links = ['name']
    list_filter = ['fault']
    search_fields = ['name']
    model_icon = 'fa fa-star'


class PriceTypeAdmin(object):
    list_display = ['id', 'name']
    search_fields = ['name']
    model_icon = 'fa fa-star'


class AreaCodeAdmin(object):
    """
    地区编码
    """
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    model_icon = 'fa fa-star'
    list_per_page = 50


# class MqttConfigAdmin(object):
#     list_display = ['url', 'port', 'timeout', 'username', 'password', 'type']
#     model_icon = 'fa fa-wifi'


xadmin.site.register(PileType, PileTypeAdmin)
xadmin.site.register(FaultCode, FaultCodeAdmin)
xadmin.site.register(PriceType, PriceTypeAdmin)
xadmin.site.register(AreaCode, AreaCodeAdmin)
# xadmin.site.register(MqttConfig, MqttConfigAdmin)