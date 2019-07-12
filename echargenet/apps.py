# coding=utf8
from django.apps import AppConfig


class EchargenetConfig(AppConfig):
    name = 'echargenet'
    verbose_name = 'e充网接口'

    def ready(self):
        from .signals import notification_connector_status
        from .signals import connector_status_init

