#-*-coding:utf-8-*-

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from codingmanager.models import AreaCode
from wxchat.models import UserInfo, UserCollection, UserBalanceResetRecord

from .paginations import PagePagination
from .serializers import UserInfoSerializer
from stationmanager.models import ChargingPile

__author__ = 'malixin'


class UserInfoRetrieveAPIView(RetrieveAPIView):
    """
    电桩列表
    """
    permission_classes = [AllowAny]
    queryset = UserInfo.objects.all()
    serializer_class = UserInfoSerializer
    lookup_field = 'openid'


class UserCollectionAPIView(APIView):
    """收藏"""
    permission_classes = (AllowAny,)

    def get(self, request):
        station_id = request.GET.get("station_id", None)
        openid = request.session.get("openid", '')

        ret = {}
        if station_id:
            counts = UserCollection.objects.filter(station_id=int(station_id), openid=openid).count()
            ret["counts"] = counts
        else:
            ret["counts"] = 0
        return Response(ret)

    def post(self, request):
        station_id = request.POST.get("station_id", None)
        openid = request.session.get("openid", '')
        if station_id:
            counts = UserCollection.objects.filter(station_id=int(station_id), openid=openid).count()
            if counts > 0:      # 已经收藏
                UserCollection.objects.filter(station_id=int(station_id), openid=openid).delete()
                return Response({"counts": 0})
            else:           # 没有收藏
                collection = UserCollection()
                collection.station_id = int(station_id)
                collection.openid = openid
                collection.save()
                return Response({"counts": 1})
        else:
            return Response({"counts": 0})


class BalanceResetAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user_id = request.POST.get("user_id", None)
        op_name = request.user.username
        # print(op_name)
        msg = {
            "status": 401,
            "message": ""
        }
        if user_id:
            try:
                user = UserInfo.objects.get(pk=user_id)
                data = {
                    'name': user.name,
                    'nickname': user.nickname,
                    'openid': user.openid,
                    'telephone': user.telephone,
                    'total_money': user.total_money,
                    'consume_money': user.consume_money,
                    'binding_amount': user.binding_amount,
                    'consume_amount': user.consume_amount,
                    'op_name': op_name,
                }
                UserBalanceResetRecord.objects.create(**data)

                user.total_money = 0
                user.consume_money = 0
                user.binding_amount = 0
                user.consume_amount = 0
                user.save(update_fields=['total_money', 'consume_money', 'binding_amount', 'consume_amount'])
                msg["status"] = 200
            except UserInfo.DoesNotExist as ex:
                msg["status"] = 200
        else:
            msg["message"] = "用户ID不正确"
        return Response(msg)

# class AreaCodeListAPIView(ListAPIView):
#     """
#     地区编码
#     """
#     permission_classes = [AllowAny]
#     queryset = AreaCode.objects.all()
#     serializer_class = AreaCodeSerializer
#     pagination_class = None
#
#     def get_queryset(self):
#         code = self.request.GET.get("code", None)
#         if code and len(code) == 2:
#             return AreaCode.objects.extra(where=['left(code,2)=%s', 'length(code)=4'], params=[code])
#         elif code and len(code) == 4:
#             return AreaCode.objects.extra(where=['left(code,4)=%s', 'length(code)=6'], params=[code])
#         else:
#             return AreaCode.objects.extra(where=['length(code)=2'])
