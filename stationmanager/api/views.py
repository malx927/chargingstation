#-*-coding:utf-8-*-
from django.db.models import Q
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from codingmanager.models import AreaCode

from .paginations import PagePagination
from .serializers import ChargingPileSerializer, AreaCodeSerializer, StationSerializer
from stationmanager.models import ChargingPile, ChargingGun, Station

__author__ = 'malixin'


class ChargingPileListAPIView(ListAPIView):
    """
    电桩列表
    """
    permission_classes = [AllowAny]
    queryset = ChargingPile.objects.all()
    serializer_class = ChargingPileSerializer

    def get_queryset(self):
        station_id = self.request.GET.get("station_id", None)
        pile_sn = self.request.GET.get("pile_sn", None)
        if station_id:
            return ChargingPile.objects.filter(station=station_id)

        if pile_sn:
            return ChargingPile.objects.filter(pile_sn=pile_sn)

        return ChargingPile.objects.all()[:10]


class AreaCodeListAPIView(ListAPIView):
    """
    地区编码
    """
    permission_classes = [AllowAny]
    queryset = AreaCode.objects.all()
    serializer_class = AreaCodeSerializer
    pagination_class = None

    def get_queryset(self):
        code = self.request.GET.get("code", None)
        if code and len(code) == 2:
            return AreaCode.objects.extra(where=['left(code,2)=%s', 'length(code)=4'], params=[code])
        elif code and len(code) == 4:
            return AreaCode.objects.extra(where=['left(code,4)=%s', 'length(code)=6'], params=[code])
        else:
            return AreaCode.objects.extra(where=['length(code)=2'])


class StationStatsView(APIView):
    """电桩统计"""
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if self.request.user.station:
            pile_counts = ChargingPile.objects.filter(station=self.request.user.station).count()
            gun_counts = ChargingGun.objects.filter(charg_pile__station=self.request.user.station).count()
        elif self.request.user.seller:
            pile_counts = ChargingPile.objects.filter(station__seller=self.request.user.seller).count()
            gun_counts = ChargingGun.objects.filter(charg_pile__station__seller=self.request.user.seller).count()
        else:
            pile_counts = ChargingPile.objects.all().count()
            gun_counts = ChargingGun.objects.all().count()

        data = {
            "piles_counts": pile_counts,
            "gun_counts": gun_counts,
        }
        return Response(data)


class StationListAPIView(ListAPIView):
    """电站列表"""
    permission_classes = [AllowAny]
    queryset = Station.objects.filter(is_show=1)
    serializer_class = StationSerializer
    pagination_class = None

    def get_queryset(self):
        city_name = self.request.GET.get("city", "北京")
        if city_name is None or len(city_name) == 0:
            city_name = "北京"
        stations = Station.objects.filter(Q(name__icontains=city_name) | Q(address__icontains=city_name)
                                            | Q(province__name__icontains=city_name) | Q(city__name__contains=city_name)
                                            | Q(district__name__icontains=city_name))
        return stations

