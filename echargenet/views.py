# coding=utf-8
import json
import random
import datetime
from decimal import Decimal
from time import sleep

from chargingorder.models import Order
from chargingorder.mqtt import server_send_charging_cmd, server_send_stop_charging_cmd
from chargingstation import settings
from django.db.models import Q, Sum, F
from django.http import HttpResponse

from .models import StationInfo, ConnectorInfo, OperatorInfo, EquipmentInfo, Token
from .paginations import PagePagination
from .serializers import StationInfoSerializer, StationStatusInfoSerializer
from .utils import get_hmac_md5, data_encode, data_decode, req_signature_check, EchargeNet, get_order_status, \
    get_equipment_connector_status
from .tasks import notification_start_charge_result, notification_stop_charge_result
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from stationmanager.models import ChargingGun, ChargingPile, ChargingPrice


def parse_request(request):
    if "query_token" not in request.get_full_path():
        auth = request.META.get('HTTP_AUTHORIZATION', None)
        if auth is None or len(auth) <= 7:
            ret = 4002
            msg = 'token error'
            errors = get_errors(ret, msg)
            return errors
        try:
            access_token = auth[7:]
            token = Token.objects.get(key=access_token)
            if token.key != access_token:
                ret = 4002
                msg = 'token error'
                errors = get_errors(ret, msg)
                return errors
        except Token.DoesNotExist:
            ret = 4002
            msg = 'token error'
            errors = get_errors(ret, msg)
            return errors
    req_data = json.loads(request.body)

    OperatorID = req_data.get("OperatorID", None)
    Data = req_data.get("Data", None)
    TimeStamp = req_data.get("TimeStamp", None)
    Seq = req_data.get("Seq", None)
    Sig = req_data.get("Sig", None)
    print(OperatorID, Data, TimeStamp, Seq, Sig)
    if OperatorID is None or Data is None or TimeStamp is None or Seq is None or Sig is None:
        print("POST parameter not enough:OperatorID,sig,TimeStamp,Data，Seq")
        ret = 4003
        msg = 'POST parameter not enough:OperatorID,sig,TimeStamp,Data，Seq'
        errors = get_errors(ret, msg)
        return errors

    # Sig验证
    sig_data = "".join((OperatorID, Data, TimeStamp, Seq))
    new_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
    if new_sig != Sig:
        print("Signature errors")
        ret = 4001
        msg = 'Signature errors'
        errors = get_errors(ret, msg)
        return errors

    result = {
        "OperatorID": OperatorID,
        "Data": Data,
    }
    return result


def get_errors(ret, msg, **kwargs):
    if kwargs is None:
        Data = {}
        Data = data_encode(**Data)
    else:
        Data = data_encode(**kwargs)

    sig_data = "".join((str(ret), msg, Data))
    sig = get_hmac_md5(settings.SIGSECRET, sig_data)
    result = {
        "Ret": ret,
        "Msg": msg,
        "Data": Data,
        "Sig": sig,
    }
    return result


class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()

    def post(self, request, *args, **kwargs):
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        print("ObtainAuthToken:", res)

        Data = res.get("Data")
        dict_data = data_decode(Data)       # 解码
        OperatorID = dict_data.get("OperatorID")
        OperatorSecret = dict_data.get("OperatorSecret")
        # OperatorID = request.POST.get("OperatorID")
        # OperatorSecret = request.POST.get("OperatorSecret")
        result = {
            "OperatorID": settings.OPERATORID,
        }
        if OperatorID != settings.ECHARGE_OPERATORID:
            result["SuccStat"] = 1
            result["FailReason"] = 1
            result["AccessToken"] = ""
            result["TokenAvailableTime"] = 0
        elif OperatorSecret != settings.OPERATORSECRET:
            result["SuccStat"] = 1
            result["FailReason"] = 2
            result["AccessToken"] = ""
            result["TokenAvailableTime"] = 0
        else:
            defaults = {
                "created": datetime.datetime.now(),
                "expire_at":  datetime.datetime.now() + datetime.timedelta(seconds=settings.EXPIRATION_DELTA),
            }
            token, created = Token.objects.update_or_create(OperatorID=OperatorID, OperatorSecret=OperatorSecret, defaults=defaults)
            result["SuccStat"] = 0
            result["FailReason"] = 0
            result["AccessToken"] = token.key
            result["TokenAvailableTime"] = (token.expire_at - token.created).total_seconds()

        # 加密
        encrypt_data = data_encode(**result)
        # 按签名规则， 用Ret+Msg+Data生成返回签名
        Ret = "0"
        Msg = "success"
        sig_data = "".join((Ret, Msg, encrypt_data))
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        ret_data = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }

        return Response(ret_data)


class StationInfoListAPIView(APIView):
    """查询运营商的充电站的信息"""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        print('StationInfoListAPIView', request.body)
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        Data = res.get("Data")
        OperatorID = res.get("OperatorID")
        # 解码
        dict_data = data_decode(Data)
        LastQueryTime = dict_data.get("LastQueryTime", None)
        # PageNo = dict_data.get("PageNo", 1)
        # PageSize = dict_data.get("PageSize", 10)

        queryset_list = StationInfo.objects.filter(OperatorID__OperatorID=settings.OPERATORID)
        if LastQueryTime:
            last_query_time = datetime.datetime.strptime(LastQueryTime, "%Y-%m-%d %H:%M:%S")
            queryset_list = queryset_list.filter(
                Q(add_time__gt=last_query_time) | Q(EquipmentInfos__add_time__gt=last_query_time) | Q(
                    EquipmentInfos__ConnectorInfos__add_time__gt=last_query_time)).distinct()

        pagination = PagePagination()
        queryset_list = pagination.paginate_queryset(queryset=queryset_list, request=request, view=self)
        serializer = StationInfoSerializer(queryset_list, many=True)

        dict_data = {
            'ItemSize': pagination.page.paginator.count,
            'PageCount': pagination.page.paginator.num_pages,
            'PageNo': pagination.page.number,
            'StationInfos': serializer.data,
        }
        # print("StationInfoListAPIView", dict_data)
        # 加密
        encrypt_data = data_encode(**dict_data)
        # 按签名规则， 用Ret+Msg+Data生成返回签名
        Ret = "0"
        Msg = "success"
        sig_data = "".join((Ret, Msg, encrypt_data))
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        return Response(result)


class StationStatusListAPIView(APIView):
    """运营商的充电站设备状态的信息"""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        print("StationStatusListAPIView:", request.body)
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        OperatorID = res.get("OperatorID")
        Data = res.get("Data")
        # 解码
        dict_data = data_decode(Data)
        StationIDs = dict_data.get("StationIDs", None)  # 字符数组
        print(StationIDs)

        total = StationInfo.objects.filter(OperatorID__OperatorID=settings.OPERATORID, StationID__in=StationIDs).count()
        queryset_list = StationInfo.objects.filter(OperatorID__OperatorID=settings.OPERATORID, StationID__in=StationIDs)

        serializer = StationStatusInfoSerializer(queryset_list, many=True)
        print(serializer.data)
        dict_data = {
            'Total': total,
            'StationStatusInfos': serializer.data,
        }
        # 加密
        encrypt_data = data_encode(**dict_data)
        # 按签名规则， 用Ret+Msg+Data生成返回签名
        Ret = 0
        Msg = "success"
        sig_data = "".join((str(Ret), Msg, encrypt_data))
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        return Response(result)


class EquipAuthAPIView(APIView):
    """
    接口名称：query_equip_auth
    接口使用方法：由基础设施运营商服务平台实现此接口，市级平台e充网服务平台方调用
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        Data = res.get("Data")
        # OperatorID = res.get("OperatorID")
        # 解码
        dict_data = data_decode(Data)
        EquipAuthSeq = dict_data.get("EquipAuthSeq", None)  # 设备认证流水号
        ConnectorID = dict_data.get("ConnectorID", None)  # 充电设备接口编码
        print(EquipAuthSeq, ConnectorID)

        connectorinfo = {}
        try:
            connector_info = ConnectorInfo.objects.get(ConnectorID=ConnectorID)  # 添加那些条件状态条件
            connectorinfo["EquipAuthSeq"] = EquipAuthSeq
            connectorinfo["ConnectorID"] = connector_info.ConnectorID
            connectorinfo["SuccStat"] = 0
            connectorinfo["FailReason"] = 0
        except ConnectorInfo.DoesNotExist as ex:
            print(ex)
            connectorinfo["EquipAuthSeq"] = EquipAuthSeq
            connectorinfo["ConnectorID"] = ConnectorID
            connectorinfo["SuccStat"] = 1
            connectorinfo["FailReason"] = 2

        # 数据加密
        encrypt_data = data_encode(**connectorinfo)
        # 数据签名, 用Ret+Msg+Data生成返回签名
        Ret = 0
        Msg = ""
        sig_data = "".join((str(Ret), Msg, encrypt_data))
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        return Response(result)


class StartChargeAPIView(APIView):
    """
    接口名称：query_start_charge
    :param: startChargeSeq, ConnectorID, QRCode
    接口使用方法：由基础设施运营商服务平台实现此接口，市级平台e充网服务平台方调用
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        Data = res.get("Data")
        OperatorID = res.get("OperatorID")
        # 解码
        dict_data = data_decode(Data)
        StartChargeSeq = dict_data.get("StartChargeSeq", None)  # 设备认证流水号
        ConnectorID = dict_data.get("ConnectorID", None)  # 充电设备接口编码
        QRCode = dict_data.get("QRCode", None)  # 二维码其他信息
        print(StartChargeSeq, ConnectorID)
        # 查询电桩状态
        pile_sn = ConnectorID[:-1]
        gun_num = ConnectorID[-1]
        pile_gun = ChargingGun.objects.select_related().filter(charg_pile__pile_sn=pile_sn, gun_num=gun_num).first()
        Ret = 0
        Msg = ""
        Data = {
            "StartChargeSeq": StartChargeSeq, "StartChargeSeqStat": 5, "ConnectorID": ConnectorID, "SuccStat": 0,
            "FailReason": 0
        }
        if pile_gun is None:
            Data["SuccStat"] = 1
            Data["FailReason"] = 1
            result = get_errors(Ret, Msg, **Data)
            return Response(result)
        if pile_gun.work_status in [2, 9]:    # 2 离线、 9故障状态 = 设备离线
            Data["SuccStat"] = 1
            Data["FailReason"] = 2
            result = get_errors(Ret, Msg, **Data)
            return Response(result)

        # 创建订单(充满为止)
        charg_mode = 0
        openid = "echargeuser"
        name = u'E充网用户'
        out_trade_no = '{0}{1}{2}{3}'.format('C', gun_num, datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
        charg_pile = pile_gun.charg_pile
        params = {
            "gun_num": pile_gun.gun_num,
            "openid": openid,
            "name": name,
            "charg_mode": charg_mode,
            "charg_type": 0,  # 0后台 01本地离线
            "out_trade_no": out_trade_no,
            "charg_pile": charg_pile,
            "start_charge_seq": StartChargeSeq,
        }
        order = Order.objects.create(**params)

        out_trade_no = order.out_trade_no
        data = {
            'pile_sn': charg_pile.pile_sn,
            'gun_num': order.gun_num,
            'out_trade_no': out_trade_no,
            'openid': order.openid,
            'charging_type': 0,  # 充电类型 1预约，0即时
            'subscribe_min': 0,
        }

        charg_policy = charg_pile.charg_policy  # 充电策略是否使用(D0：1使用充电策略，0系统默认策略)(电站还是电桩为准)
        data["use_policy_flag"] = charg_policy
        # 1使用充电策略
        if charg_policy == 1:
            data["continue_charg_status"] = 0  # 断网可继续充电  1断网可继续充电，0不可以(那些用户？)
            data["occupy_status"] = charg_pile.occupy_status  # 收取占位费 1收取占位费，0不收取
            data["subscribe_status"] = charg_pile.subscribe_status  # 收取预约费
            data["low_fee_status"] = charg_pile.low_offset  # 收取小电流补偿费
            data["low_restrict_status"] = charg_pile.low_restrict  # 限制小电流输出

        charging_policy_value = 0
        data["charging_policy_value"] = charging_policy_value

        server_send_charging_cmd(**data)
        sleep(0.2)
        try:
            new_order = Order.objects.get(out_trade_no=out_trade_no)
            Data["StartChargeSeqStat"] = get_order_status(new_order.charg_status.id)

            Data["SuccStat"] = 0
            Data["FailReason"] = 0
        except Order.DoesNotExist as ex:
            Data["StartChargeSeqStat"] = 5
            Data["SuccStat"] = 1
            Data["FailReason"] = 3

        encrypt_data = data_encode(**Data)   # 数据加密
        # 数据签名, 用Ret+Msg+Data生成返回签名
        Ret = 0
        Msg = ""
        sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        # 推送启动充电结果 异步延时5秒
        notification_start_charge_result.delay(order.start_charge_seq, ConnectorID)
        return Response(result)


class StopChargeAPIView(APIView):
    """
    请求停止充电, 使用要求：请求停止充电接口响应时间应不大于1秒
    接口名称：query_stop_charge
    :param: startChargeSeq, ConnectorID
    接口使用方法：由基础设施运营商服务平台实现此接口，市级平台e充网服务平台方调用
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        Data = res.get("Data")
        OperatorID = res.get("OperatorID")
        # 解码
        dict_data = data_decode(Data)
        StartChargeSeq = dict_data.get("StartChargeSeq", None)  # 设备认证流水号
        ConnectorID = dict_data.get("ConnectorID", None)  # 充电设备接口编码
        print(StartChargeSeq, ConnectorID)
        # 查询电桩状态
        pile_sn = ConnectorID[:-1]
        gun_num = ConnectorID[-1]
        pile_gun = ChargingGun.objects.filter(charg_pile__pile_sn=pile_sn, gun_num=gun_num).first()
        Ret = 0
        Msg = ""
        Data = {
            "StartChargeSeq": StartChargeSeq, "StartChargeSeqStat": 5, "SuccStat": 0, "FailReason": 0
        }
        if pile_gun is None:
            Data["SuccStat"] = 1
            Data["FailReason"] = 1
            result = get_errors(Ret, Msg, **Data)
            return Response(result)
        if pile_gun.work_status in [2, 9]:  # 1 离线、 4故障状态 = 设备离线
            Data["SuccStat"] = 1
            Data["FailReason"] = 2
            result = get_errors(Ret, Msg, **Data)
            return Response(result)

        # 查询订单
        try:
            order = Order.objects.get(start_charge_seq=StartChargeSeq)
            stop_data = {
                "pile_sn": order.charg_pile.pile_sn,
                "gun_num": order.gun_num,
                "openid": order.openid,
                "out_trade_no": order.out_trade_no,
                "consum_money": int(order.consum_money.quantize(Decimal("0.01")) * 100),
                "total_reading": int(order.get_total_reading() / Decimal(settings.FACTOR_READINGS)),
                "stop_code": 0,  # 0 主动停止，1被动响应，2消费清单已结束或不存在
            }
            server_send_stop_charging_cmd(**stop_data)
            sleep(0.2)
            Data["StartChargeSeqStat"] = get_order_status(order.charg_status.id)

            Data["SuccStat"] = 0
            Data["FailReason"] = 0
        except Order.DoesNotExist as ex:
            Data["StartChargeSeqStat"] = 5
            Data["SuccStat"] = 1
            Data["FailReason"] = 4

        encrypt_data = data_encode(**Data)  # 数据加密
        # 数据签名, 用Ret+Msg+Data生成返回签名
        sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        # 推送停止充电结果 异步延时5秒
        notification_stop_charge_result.delay(StartChargeSeq, ConnectorID)
        return Response(result)


class EquipChargeStatusAPIView(APIView):
    """
    接口名称：query_equip_charge_status
    使用要求：查询接口返回结果响应时间应不大于1秒。充电桩正在充电中状态时，市级平台e充网可
    主动查询充电状态，查询频率大于120秒
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        Data = res.get("Data")
        OperatorID = res.get("OperatorID")
        # 解码
        dict_data = data_decode(Data)
        StartChargeSeq = dict_data.get("StartChargeSeq", None)  # 设备认证流水号
        # 查询电桩状态
        try:
            order = Order.objects.get(start_charge_seq=StartChargeSeq)
            gun = ChargingGun.objects.get(charg_pile=order.charg_pile, gun_num=order.gun_num)

            Data = {
               "StartChargeSeq": StartChargeSeq,
            }
            stat = get_order_status(order.charg_status.id)
            Data["StartChargeSeqStat"] = stat

            Data["ConnectorID"] = "{0}{1}".format(order.charg_pile.pile_sn, order.gun_num)

            connector_status = get_equipment_connector_status(gun.work_status, order.charg_status.id)
            Data["ConnectorStatus"] = connector_status
            Data["CurrentA"] = 0
            Data["VoltageA"] = 0
            Data["Soc"] = order.end_soc
            if order.begin_time:
                Data["StartTime"] = order.begin_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                Data["StartTime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if order.end_time:
                Data["EndTime"] = order.end_time.strftime("%Y-%m-%d %H:%M:%S")
            else:
                Data["EndTime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            Data["TotalPower"] = float(order.get_total_reading())
            Data["ElecMoney"] = float(order.consum_money)
        except Order.DoesNotExist as ex:
            Ret = 4004
            Msg = "StartChargeSeq Does Not Exist"
            Data ={"StartChargeSeq": StartChargeSeq}
            result = get_errors(Ret, Msg, **Data)
            return Response(result)
        except ChargingGun.DoesNotExist as ex:
            Ret = 4004
            Msg = "ConnectorID Does Not Exist"
            Data ={"StartChargeSeq": StartChargeSeq}
            result = get_errors(Ret, Msg, **Data)
            return Response(result)

        encrypt_data = data_encode(**Data)  # 数据加密
        # 数据签名, 用Ret+Msg+Data生成返回签名
        Ret = 0
        Msg = ""
        sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        return Response(result)


class StationStatsAPIView(APIView):
    """
    此查询用于定期获取每个充电站，在某个周期内的统计信息
    接口名称： query_station_stats
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        Data = res.get("Data")
        OperatorID = res.get("OperatorID")
        # 解码
        dict_data = data_decode(Data)
        StationID = dict_data.get("StationID", None)  # 充电站
        StartTime = dict_data.get("StartTime", None)  # 统计开始时间
        EndTime = dict_data.get("EndTime", None)  # 统计结束时间
        # 查询电桩状态
        start_time = datetime.datetime.strptime(StartTime, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.datetime.strptime(EndTime, '%Y-%m-%d %H:%M:%S')
        # 充电站
        station_stats = Order.objects.filter(charg_pile__station__id=StationID, charg_pile__is_subsidy=1, end_time__date__range=(start_time, end_time))\
            .aggregate(
            StationElectricity=Sum(F("end_reading") - F("begin_reading"))
            )

        StationStats = {
            "StationID": StationID,
            "StartTime": StartTime,
            "EndTime": EndTime,
            "StationElectricity": station_stats["StationElectricity"],
        }
        # 充电桩统计
        equipment_stats = Order.objects.filter(charg_pile__station__id=StationID, charg_pile__is_subsidy=1, end_time__date__range=(start_time, end_time))\
            .values("charg_pile__id")\
            .annotate(EquipmentElectricity=Sum(F("end_reading") - F("begin_reading")))

        EquipmentStatsInfos = []
        for equip_stats in equipment_stats:
            EquipmentStatsInfo ={}
            EquipmentID = equip_stats["charg_pile__id"]
            EquipmentStatsInfo["EquipmentID"] = EquipmentID
            EquipmentStatsInfo["EquipmentElectricity"] = equip_stats["EquipmentElectricity"]
            # 枪口统计
            connector_stats = Order.objects.filter(charg_pile__id=EquipmentID, charg_pile__is_subsidy=1,
                                                   end_time__date__range=(start_time, end_time)) \
                .values("gun_num") \
                .annotate(ConnectorElectricity=Sum(F("end_reading") - F("begin_reading")))
            charg_pile = ChargingPile.objects.get(pk=EquipmentID)
            ConnectorStatsInfos = []
            for conn_stats in connector_stats:
                ConnectorStatsInfo = {}
                ConnectorStatsInfo["ConnectorID"] = '{0}{1}'.format(charg_pile.pile_sn, conn_stats["gun_num"])
                ConnectorStatsInfo["ConnectorElectricity"] = conn_stats["ConnectorElectricity"]
                ConnectorStatsInfos.append(ConnectorInfo)

            EquipmentStatsInfo["ConnectorStatsInfos"] = ConnectorStatsInfos

            EquipmentStatsInfos.append(EquipmentStatsInfo)

        StationStats["EquipmentStatsInfos"] = EquipmentStatsInfos

        crypt_data = {
            "StationStats": StationStats
        }

        encrypt_data = data_encode(**crypt_data)  # 数据加密
        # 数据签名, 用Ret+Msg+Data生成返回签名
        Ret = 0
        Msg = ""
        sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        return Response(result)


class EquipBusinessPolicyAPIView(APIView):
    """
    接口名称：query_equip_business_policy
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        res = parse_request(request)
        if "Ret" in res:
            return Response(res)

        Data = res.get("Data")
        OperatorID = res.get("OperatorID")
        # 解码
        dict_data = data_decode(Data)
        EquipBizSeq = dict_data.get("EquipBizSeq", None)  # 业务策略查询流水号
        ConnectorID = dict_data.get("ConnectorID", None)  # 充电设备接口编码
        # 充电站
        try:
            connector_info = ConnectorInfo.objects.get(ConnectorID=ConnectorID)
        except ConnectorInfo.DoesNotExist as ex:
            Ret = 4004
            Msg = "ConnectorID Does Not Exist"
            Data = {
                "EquipBizSeq": EquipBizSeq,
                "ConnectorID": ConnectorID,
                "SuccStat": 1,
                "FailReason": 0,
            }
            result = get_errors(Ret, Msg, **Data)
            return Response(result)
        station_id = int(connector_info.EquipmentID.StationID.StationID)
        station_price = ChargingPrice.objects.filter(station__id=station_id, default_flag=1).first()
        if station_price is None:
            Ret = 4004
            Msg = "business policy  does not exist"
            Data = {
                "EquipBizSeq": EquipBizSeq,
                "ConnectorID": ConnectorID,
                "SuccStat": 1,
                "FailReason": 1,
            }
            result = get_errors(Ret, Msg, **Data)
            return Response(result)

        SumPeriod = station_price.prices.count()
        prices = station_price.prices.all()

        PolicyInfos = []
        for item in prices:
            policy_info = {}
            policy_info["StartTime"] = item.begin_time.strftime("%H%M%S")
            policy_info["ElecPrice"] = float(item.price)
            policy_info["SevicePrice"] = 0
            PolicyInfos.append(policy_info)

        Data = {
            "EquipBizSeq": EquipBizSeq,
            "ConnectorID": ConnectorID,
            "SuccStat": 0,
            "FailReason": 0,
            "SumPeriod": SumPeriod,
            "PolicyInfos": PolicyInfos,
        }

        encrypt_data = data_encode(**Data)  # 数据加密
        # 数据签名, 用Ret+Msg+Data生成返回签名
        Ret = 0
        Msg = ""
        sig_data = "{0}{1}{2}".format(str(Ret), Msg, encrypt_data)
        ret_sig = get_hmac_md5(settings.SIGSECRET, sig_data)
        result = {
            "Ret": Ret,
            "Msg": Msg,
            "Data": encrypt_data,
            "Sig": ret_sig,
        }
        return Response(result)

