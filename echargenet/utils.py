# -*-coding:utf-8-*-
import json
from datetime import datetime
import hashlib
import hmac
import time
import logging

import redis
import requests
from Crypto.Cipher import AES
import base64
from chargingstation import settings

logger = logging.getLogger("django")

BLOCK_SIZE = 16  # Bytes
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]


def get_order_status(charg_status):
    if charg_status is None:
        return 5
    if 2 > charg_status >= 1:
        return 1        # 启动中
    elif 6 >= charg_status >= 2:
        return 2        # 充电中
    elif charg_status == 7:
        return 3        # 停止中
    elif charg_status == 0 or 98 >= charg_status >= 91:
        return 4        # 已结束
    else:
        return 5        # 未知


def get_equipment_connector_status(work_status, charg_status):
    if work_status == 9:
        return 0  # 离网
    elif work_status == 0:
        return 1  # 空闲
    elif work_status == 1 and 5 >= charg_status >= 1:
        return 2    # 占用（未充电)
    elif work_status == 3:
        return 2  # 占用（未充电)
    elif work_status == 1 and charg_status == 6:
        return 3    # 占用（充电中）
    elif work_status == 2 and 80 >= charg_status >= 11:
        return 255  # 故障


def data_encode(**data):
    ret_data = AESCipher(settings.DATASECRET, settings.DATASECRETIV).encrypt(json.dumps(data))
    return ret_data


def data_decode(crypt_data):
    ret_decrypt_data = AESCipher(settings.DATASECRET, settings.DATASECRETIV).decrypt(crypt_data)
    return json.loads(ret_decrypt_data)


def resp_signature_check(**kwargs):
    ret = kwargs.get("Ret")
    msg = kwargs.get("Msg")
    data = kwargs.get("Data")
    sig = kwargs.get("Sig")
    sig_data = '{}{}{}'.format(ret, msg, data)
    new_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
    return sig == new_sig


def req_signature_check(**kwargs):
    operatorid = kwargs.get("OperatorID")
    data = kwargs.get("Data")
    timestamp = kwargs.get("TimeStamp")
    seq = kwargs.get("Seq")
    sig = kwargs.get("Sig")
    sig_data = '{}{}{}{}'.format(operatorid, data, timestamp, seq)
    new_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
    return sig == new_sig


class AESCipher:
    """
    AES CBC PKCS5Padding 加解密
    """
    def __init__(self, key, iv):
        # 加密需要的key值
        self.key = str.encode(key)
        self.iv = str.encode(iv)

    def encrypt(self, raw):
        raw = pad(raw)
        # 通过key值，使用CBC模式进行加密
        data = str.encode(raw)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        # 返回得到加密后的字符串进行解码然后进行64位的编码
        return base64.b64encode(cipher.encrypt(data)).decode('utf8')

    def decrypt(self, enc):
        # 首先对已经加密的字符串进行解码
        enc = base64.b64decode(enc)
        # 通过key值，使用ECB模式进行解密
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(enc)).decode('utf8')


def get_hmac_md5(key, data):
    """HMAC-MD5 参数签名"""
    ret = hmac.new(bytes(key, encoding='utf-8'), bytes(data, encoding='utf-8'), hashlib.md5).hexdigest()
    return ret.upper()


class EchargeNet(object):
    # E_CHARGE_URL = 'http://hlht.test.zc3u.com/evcs/20160701/'   # 测试环境
    E_CHARGE_URL = 'http://hlht.zc3u.com/evcs/20160701/'   # 运行环境
    HEADERS = {'content-type': 'application/json;charset=utf-8'}
    ACCESS_TOKEN_KEY = "{0}_{1}".format(settings.OPERATORID, "access_token")
    ACCESS_TOKEN_EXPIRES_AT = "{0}_{1}".format(settings.OPERATORID, "access_token_expires_at")

    def __init__(self, redis_url, port):
        self.redis_url = redis_url
        self.port = port

    def connect_redis(self):
        """链接Redis"""
        pool = redis.ConnectionPool(host=self.redis_url, port=self.port)
        try:
            redis_client = redis.Redis(connection_pool=pool)
        except Exception as err:
            raise err

        return redis_client

    def _post(self, url, token=None, **kwargs ):
        if kwargs is None:
            return None
        encrypt_data = data_encode(**kwargs)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        seq = '0001'
        sig_data = "".join((settings.OPERATORID, encrypt_data, timestamp, seq))
        sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        send_data = {
            "OperatorID": settings.OPERATORID,
            "Data": encrypt_data,
            "TimeStamp": timestamp,
            "Seq": seq,
            "Sig": sig,
        }
        if token is not None:
            self.HEADERS["Authorization"] = 'Bearer {}'.format(token)
        else:
            if "Authorization" in self.HEADERS:
                del self.HEADERS["Authorization"]
        logger.info(send_data)
        r = requests.post(url, data=json.dumps(send_data), headers=self.HEADERS)
        result = r.json()
        return result

    def get_query_token(self):
        """获取token"""
        r = self.connect_redis()
        access_token = r.get(self.ACCESS_TOKEN_KEY)
        b_expires_at = r.get(self.ACCESS_TOKEN_EXPIRES_AT)
        logger.info("{}--{}".format(access_token, b_expires_at))
        if access_token and b_expires_at:
            timestamp = time.time()
            expires_at = int(b_expires_at)
            logger.info("{}--{}".format(timestamp, timestamp))
            if expires_at - timestamp > 60:
                res = {
                    "success": True,
                    "access_token": access_token.decode(),
                }
                return res

        data = {
            'OperatorID': settings.OPERATORID,
            'OperatorSecret': settings.OPERATORSECRET,
        }
        url = '{0}{1}'.format(self.E_CHARGE_URL, 'query_token')
        result = self._post(url, **data)
        logger.info(result)
        if "Ret" in result and result["Ret"] == 0:
            # 解密
            ret_crypt_data = result["Data"]
            dict_decrpt_data = data_decode(ret_crypt_data)
            logger.info(dict_decrpt_data)
            # # 获取到code值
            if dict_decrpt_data["SuccStat"] == 0:
                # 设置token
                access_token = dict_decrpt_data["AccessToken"]
                token_available_time = dict_decrpt_data["TokenAvailableTime"]

                logger.info("{}--{}".format(access_token, token_available_time))

                r.set(self.ACCESS_TOKEN_KEY, access_token, token_available_time)
                expires_at = int(time.time()) + token_available_time
                r.set(self.ACCESS_TOKEN_EXPIRES_AT, expires_at)
                res = {
                    "success": True,
                    "access_token": access_token,
                }
            else:
                res = {
                    "success": False,
                    "ret_code": result["SuccStat"],
                    "error_msg": result["FailReason"],
                }
        else:
            res = {
                "success": False,
                "ret_code": result["Ret"],
                "error_msg": result["Msg"],
            }
        return res

    def notification_station_status(self, connector_id, status):
        """
            信号触发
            当设备状态发生变化，立即推送最新状态到市级平台 e 充网。
        """
        url = '{0}{1}'.format(self.E_CHARGE_URL, 'notification_stationStatus')
        # 获得token
        dict_token = self.get_query_token()
        if dict_token["success"]:
            token = dict_token["access_token"]
        else:
            logger.info("access token error!")
            return 4002

        notification_stationStatusData = {
                    "ConnectorStatusInfo": {
                        "ConnectorID": connector_id,
                        "Status": status,
                    }
        }

        logger.info(notification_stationStatusData)
        result = self._post(url, token, **notification_stationStatusData)
        logger.info(result)

        if "Ret" in result and result["Ret"] == 0:
            # 解密
            ret_crypt_data = result["Data"]
            dict_decrpt_data = data_decode(ret_crypt_data)
            # 获取到code值
            status = dict_decrpt_data["Status"]
            return status
        else:
            logger.info(result["Msg"])
            return result["Ret"]

    # 接口名称：query_equip_auth
    # 接口使用方法：由基础设施运营商服务平台实现此接口，市级平台e充网服务平台方调用

    def notification_start_charge_result(self, *args, **kwargs):
        url = '{0}{1}'.format(self.E_CHARGE_URL, 'notification_start_charge_result')
        # 获得token
        dict_token = self.get_query_token()
        if dict_token["success"]:
            token = dict_token["access_token"]
        else:
            logger.info("access token error!")
            return 4002

        result = self._post(url, token, **kwargs)
        logger.info(result)

        if "Ret" in result and result["Ret"] == 0:
            # 解密
            ret_crypt_data = result["Data"]
            dict_decrpt_data = data_decode(ret_crypt_data)
            # 获取到code值
            logger.info(dict_decrpt_data["StartChargeSeq"])
            status = dict_decrpt_data["SuccStat"]
            return status
        else:
            logger.info(result["Msg"])
            return result["Ret"]

    def notification_equip_charge_status(self, *args, **kwargs):
        url = '{0}{1}'.format(self.E_CHARGE_URL, 'notification_equip_charge_status')
        # 获得token
        dict_token = self.get_query_token()
        if dict_token["success"]:
            token = dict_token["access_token"]
        else:
            logger.info("access token error!")
            return 4002

        result = self._post(url, token, **kwargs)
        logger.info(result)

        if "Ret" in result and result["Ret"] == 0:
            # 解密
            ret_crypt_data = result["Data"]
            dict_decrpt_data = data_decode(ret_crypt_data)
            # 获取到code值
            logger.info(dict_decrpt_data["StartChargeSeq"])
            status = dict_decrpt_data["SuccStat"]
            return status
        else:
            logger.info(result["Msg"])
            return result["Ret"]

    def notification_stop_charge_result(self, *args, **kwargs):
        url = '{0}{1}'.format(self.E_CHARGE_URL, 'notification_stop_charge_result')
        # 获得token
        dict_token = self.get_query_token()
        if dict_token["success"]:
            token = dict_token["access_token"]
        else:
            logger.info("access token error!")
            return 4002  # Token 错误

        result = self._post(url, token, **kwargs)
        logger.info(result)

        if "Ret" in result and result["Ret"] == 0:
            # 解密
            ret_crypt_data = result["Data"]
            dict_decrpt_data = data_decode(ret_crypt_data)
            # 获取到code值
            logger.info(dict_decrpt_data["StartChargeSeq"])

            status = dict_decrpt_data["SuccStat"]
            return status
        else:
            logger.info(result["Msg"])
            return result["Ret"]

    def notification_charge_order_info_for_bonus(self, *args, **kwargs):
        url = '{0}{1}'.format(self.E_CHARGE_URL, 'notification_charge_order_info_for_bonus')
        # 获得token
        dict_token = self.get_query_token()
        if dict_token["success"]:
            token = dict_token["access_token"]
        else:
            logger.info("access token error!")
            result = {
                "Ret": 4002,
                "Msg": "access token error!",
            }
            return result  # Token 错误

        result = self._post(url, token, **kwargs)
        logger.info(result)
        return result

    def check_charge_orders(self, *args, **kwargs):
        url = '{0}{1}'.format(self.E_CHARGE_URL, 'check_charge_orders')
        # 获得token
        dict_token = self.get_query_token()
        if dict_token["success"]:
            token = dict_token["access_token"]
        else:
            logger.info("access token error!")
            result = {
                "Ret": 4002,
                "Msg": "access token error!",
            }
            return result  # Token 错误

        result = self._post(url, token, **kwargs)
        logger.info("check_charge_orders:", result)
        return result
