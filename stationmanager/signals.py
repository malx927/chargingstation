# coding=utf-8
import logging

from django.db.models.signals import post_init, post_save, post_delete
from django.dispatch import receiver

from chargingstation import settings
from .models import Seller, Station, ChargingPile, ChargingGun
from echargenet.models import OperatorInfo, StationInfo, EquipmentInfo, ConnectorInfo


# 运营商
@receiver(post_init, sender=Seller)
def operator_info_init(instance, **kwargs):
    instance.old_org_code = instance.org_code


@receiver(post_save, sender=Seller)
def update_operator_info(sender, instance, created, **kwargs):
    # if instance.org_code is None:
    #     return
    # print(instance.old_org_code, created)
    # if not created and instance.old_org_code != instance.org_code:
    #     OperatorInfo.objects.filter(OperatorID=instance.old_org_code).delete()
    #     operator_info = {
    #         "OperatorID": instance.org_code,
    #         "OperatorName": instance.name,
    #         "OperatorTel1": instance.telephone,
    #     }
    #     OperatorInfo.objects.create(**operator_info)
    # else:
    ID = instance.id
    defaults = {
        "OperatorID": instance.org_code,
        "OperatorName": instance.name,
        "OperatorTel1": instance.telephone,
    }
    OperatorInfo.objects.update_or_create(ID=ID, defaults=defaults)


@receiver(post_delete, sender=Seller)
def operator_info_delete(sender, instance, **kwargs):
    OperatorInfo.objects.filter(ID=instance.id).delete()


# 充电站
@receiver(post_save, sender=Station)
def update_station_info(sender, instance, created, **kwargs):
        try:
            StationID = instance.id
            ID = instance.seller.id
            oper_info = OperatorInfo.objects.get(ID=ID)
            defaults = {
                "OperatorID": oper_info,
                "EquipmentOwnerID": instance.equip_owner_id,
                "StationName": instance.name,
                "AreaCode": instance.district.code,
                "Address": instance.address,
                "ServiceTel": instance.telephone,
                "StationType": instance.station_type,
                "StationStatus": instance.station_status,
                "StationLng": instance.longitude,
                "StationLat": instance.latitude,
                "Construction": instance.construction,
            }

            StationInfo.objects.update_or_create(StationID=str(StationID), defaults=defaults)

        except OperatorInfo.DoesNotExist as ex:
            pass


@receiver(post_delete, sender=Station)
def station_info_delete(sender, instance, **kwargs):
    StationInfo.objects.filter(StationID=instance.id).delete()


# 充电站
@receiver(post_save, sender=ChargingPile)
def update_equipment_info(sender, instance, created, **kwargs):
        try:
            EquipmentID = instance.id
            StationID = instance.station.id
            station_info = StationInfo.objects.get(StationID=str(StationID))
            if instance.pile_type.id in [1, 2]:
                EquipmentType = 1
            elif instance.pile_type.id == 3:
                EquipmentType = 3
            elif instance.pile_type.id in [5, 6]:
                EquipmentType = 2
            else:
                EquipmentType = 5

            defaults = {
                "EquipmentName": instance.name,
                "EquipmentType": EquipmentType,
                "Power": instance.power,
                "StationID": station_info,
            }

            EquipmentInfo.objects.update_or_create(EquipmentID=str(EquipmentID), defaults=defaults)
        except StationInfo.DoesNotExist as ex:
            pass


@receiver(post_delete, sender=ChargingPile)
def equipment_info_delete(sender, instance, **kwargs):
    EquipmentInfo.objects.filter(EquipmentID=str(instance.id)).delete()


# 充电枪
@receiver(post_save, sender=ChargingGun)
def update_connector_info(sender, instance, created, **kwargs):
        try:
            ID = instance.id
            ConnectorID = '{}{}'.format(instance.charg_pile.pile_sn, instance.gun_num)
            EquipmentID = instance.charg_pile.id
            equipment_info = EquipmentInfo.objects.get(EquipmentID=str(EquipmentID))
            connector_type = 0
            if instance.work_status == 9:
                connector_type = 0          # 离网
            elif instance.work_status == 0:
                connector_type = 1          # 空闲
            elif instance.work_status == 1 and 5 >= instance.charg_status.id >= 0:
                connector_type = 2
            elif instance.work_status == 3:
                connector_type = 2
            elif instance.work_status == 1 and instance.charg_status.id == 6:
                connector_type = 3
            elif instance.work_status == 2:
                connector_type = 255
            print("update_connector_info")
            defaults = {
                "ConnectorID": ConnectorID,
                "ConnectorType": instance.gun_type,
                "VoltageUpperLimits": instance.voltage_upper_limits,
                "VoltageLowerLimits": instance.voltage_lower_limits,
                "Current": instance.current,
                "Power": instance.power,
                "EquipmentID": equipment_info,
                "NationalStandard": instance.nationalstandard,
                "Status": connector_type,
            }

            ret = ConnectorInfo.objects.update_or_create(ID=str(ID), defaults=defaults)
            logging.info(ret)
        except EquipmentInfo.DoesNotExist as ex:
            logging.warning(ex)


@receiver(post_delete, sender=ChargingGun)
def connector_info_delete(sender, instance, **kwargs):
    ConnectorInfo.objects.filter(ID=str(instance.id)).delete()

