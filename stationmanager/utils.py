# -*-coding:utf-8-*-
import hashlib
import hmac
import qrcode
import math
import time

import redis
from Crypto.Cipher import AES
import base64

from chargingstation import settings

__author__ = 'malxin'


def connect_redis():
    """
    链接 redis
    :return:
    """
    pool = redis.ConnectionPool(host=settings.MQTT_REDIS_URL, port=settings.MQTT_REDIS_PORT, db=2)
    try:
        redis_client = redis.Redis(connection_pool=pool)
    except Exception as err:
        raise err

    return redis_client


# 创建二维码
def create_qrcode(content):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image()
    return img


def get_mqtt_param(product_key, device_name, device_secret):
        ProductKey = product_key
        ClientId = device_name
        DeviceName = device_name
        DeviceSecret = device_secret

        signmethod = "hmacsha1"
        us = math.modf(time.time())[0]
        ms = int(round(us * 1000))
        timestamp = str(ms)
        data = "".join(("clientId", ClientId, "deviceName", DeviceName,
                        "productKey", ProductKey, "timestamp", timestamp))

        ret = hmac.new(bytes(DeviceSecret, encoding='utf-8'), bytes(data, encoding='utf-8'), hashlib.sha1).hexdigest()
        sign = ret
        client_id = "".join((ClientId, "|securemode=3", ",signmethod=", signmethod, ",timestamp=", timestamp, "|"))
        username = "".join((DeviceName, "&", ProductKey))
        password = sign
        return client_id, username, password


