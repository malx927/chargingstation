# coding=utf-8
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from chargingstation import settings
from echargenet.models import ConnectorInfo
from .utils import EchargeNet


@receiver(post_init, sender=ConnectorInfo)
def connector_status_init(instance, **kwargs):
    instance.org_Status = instance.Status


@receiver(post_save, sender=ConnectorInfo)
def notification_connector_status(sender, instance, created, update_fields, **kwargs):
    print(created, instance.org_Status, instance.Status)
    # if not created and instance.org_Status != instance.Status:
    #     echarge = EchargeNet(settings.MQTT_REDIS_URL, settings.MQTT_REDIS_PORT)
    #     status = echarge.notification_station_status(instance.ConnectorID, instance.Status)
    #     print("signal ret value:", status)
