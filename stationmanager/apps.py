# coding=utf8
from django.apps import AppConfig


class StationmanagerConfig(AppConfig):
    name = 'stationmanager'
    verbose_name = u'充电桩管理'

    def ready(self):
        from .signals import update_operator_info
        from .signals import operator_info_init
        from .signals import operator_info_delete
        from .signals import update_station_info
        from .signals import station_info_delete
        from .signals import update_equipment_info
        from .signals import equipment_info_delete
        from .signals import update_connector_info
        from .signals import connector_info_delete
