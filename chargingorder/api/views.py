#-*-coding:utf-8-*-
import datetime

from django.db.models import Sum, Count, Q, F, DecimalField, FloatField, IntegerField
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from chargingorder.models import Order
from codingmanager.models import AreaCode

from .paginations import PagePagination
# from .serializers import ChargingPileSerializer, AreaCodeSerializer
from stationmanager.models import ChargingPile

__author__ = 'malixin'


class OrderDayStats(APIView):
    """订单日统计"""
    def get(self, request, *args, **kwargs):
        flag = request.GET.get("flag", None)
        results = {
            "readings": 0,
            "counts": 0,
            "total_fees": 0,
            "times": 0,
        }
        if flag is None:    # 当天
            cur_time = datetime.datetime.now().date()
            results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=cur_time)\
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("cash_fee"),
                           times=Sum((F("end_time") - F("begin_time"))/(1000000*60), output_field=IntegerField()))
        elif flag == "1":   # 昨天
            yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
            yesterday = yesterday.date()
            results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=yesterday) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("cash_fee"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60), output_field=IntegerField()))

        elif flag == "2":   # 任意天
            sdate = request.GET.get("sdate", None)
            if sdate:
                search_date = datetime.datetime.strptime(sdate, "%Y-%m-%d")
                s_date = search_date.date()
                results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__date=s_date) \
                    .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("cash_fee"),
                               times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60), output_field=IntegerField()))

        return Response(results)


class OrderMonthStats(APIView):
    """月统计"""
    def get(self, request, *args, **kwargs):
        month = request.GET.get("month", None)

        if month is None:  # 当月
            cur_time = datetime.datetime.now()
            results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__year=cur_time.year, begin_time__month=cur_time.month) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("cash_fee"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60), output_field=IntegerField()))
        else:  # 任意月
            s_date = datetime.datetime.strptime(month, "%Y-%m")
            results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__year=s_date.year, begin_time__month=s_date.month) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("cash_fee"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60), output_field=IntegerField()))

        return Response(results)


class OrderYearStats(APIView):
    """年统计"""
    def get(self, request, *args, **kwargs):
        year = request.GET.get("year", None)

        if year is None:  # 当年
            cur_time = datetime.datetime.now()
            results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__year=cur_time.year) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("cash_fee"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60), output_field=IntegerField()))
            print(results)
        else:  # 任意年

            results = Order.objects.filter(status=2, pay_time__isnull=False, begin_time__year=int(year)) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("cash_fee"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60), output_field=IntegerField()))

        return Response(results)

# class ChargingPileListAPIView(ListAPIView):
#     """
#     电桩列表
#     """
#     permission_classes = [AllowAny]
#     queryset = ChargingPile.objects.all()
#     serializer_class = ChargingPileSerializer
#
#     def get_queryset(self):
#         station_id = self.request.GET.get("station_id", None)
#         pile_sn = self.request.GET.get("pile_sn", None)
#         if station_id:
#             return ChargingPile.objects.filter(station=station_id)
#
#         if pile_sn:
#             return ChargingPile.objects.filter(pile_sn=pile_sn)
#
#         return ChargingPile.objects.all()[:10]
#
#
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

# #狗配种
# class DogbreedListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = DogBreed.objects.all()
#     serializer_class = DogbreedListSerializer
#     def get_queryset(self):
#         return  DogBreed.objects.filter(is_show=1)
#
# class DogBreedDetailAPIView(RetrieveAPIView):
#     queryset = DogBreed.objects.all()
#     serializer_class = DogBreedDetailSerializer
#     permission_classes = [AllowAny]
#
#
# class DogLossDetailAPIView(RetrieveAPIView):
#     queryset = DogLoss.objects.all()
#     serializer_class = DogLossDetailSerializer
#     permission_classes = [AllowAny]
#
# #寻找宠物主人
# class DogOwnerListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = DogOwner.objects.all()
#     serializer_class = DogOwnerSerializer
#     def get_queryset(self):
#         return  DogOwner.objects.filter(is_show=1)
#
#
# #宠物领养
# class DogadoptListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = DogAdoption.objects.all()
#     serializer_class = DogadoptListSerializer
#     def get_queryset(self):
#         return  DogAdoption.objects.filter(is_show=1)
#
#
# #宠物送养
# class DogdeliveryListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = DogDelivery.objects.all()
#     serializer_class = DogdeliverySerializer
#     def get_queryset(self):
#         return  DogDelivery.objects.filter(is_show=1)
#
#
# class DogdeliveryDeliveryAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = DogDelivery.objects.all()
#     serializer_class = DogdeliveryDetailSerializer
#
# #寻找宠物主人
# class DogBuyListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = DogBuy.objects.all()
#     serializer_class = DogBuySerializer
#     def get_queryset(self):
#         return  DogBuy.objects.filter(is_show=1)
#
#
# class DogSaleListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = DogSale.objects.all()
#     serializer_class = DogSaleSerializer
#     def get_queryset(self):
#         return  DogSale.objects.filter(is_show=1)
#
#
# #新手课堂
# class DogFreshmanListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = Freshman.objects.all()
#     serializer_class = DogfreshmanSerializer
#     def get_queryset(self):
#         return  Freshman.objects.filter(is_show=1)
#
#
# #加盟宠物医疗机构
# class DogInstitutionListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = Doginstitution.objects.all()
#     serializer_class = DogInstitutionSerializer
#     def get_queryset(self):
#         return  Doginstitution.objects.filter(is_show=1)
#
#
# class SwiperImageListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = SwiperImage.objects.all()
#     serializer_class = SwiperImageListSerializer
#
#     def get_queryset(self):
#         return SwiperImage.objects.filter(is_show=1)
#
#
# class AreaCodeListAPIView(ListAPIView):
#     permission_classes = [AllowAny]
#     queryset = AreaCode.objects.all()
#     serializer_class = CodeProvinceSerializer
#     pagination_class = None
#
#     def get_queryset(self):
#         return AreaCode.objects.extra(where=['length(code)=2'])
#
#
#
# class MyInfoListAPIView(APIView):
#     permission_classes = (AllowAny,)
#
#     def get(self, request):
#         type = request.GET.get('type',None)
#         openid = request.session.get('openid',None)
#         print(type,openid)
#         if type == 'loss' and  openid:
#             queryset_list = DogLoss.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogLossSerializer(queryset_list, many=True)
#             print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         elif type=='owner' and openid:
#             queryset_list = DogOwner.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogOwnerSerializer(queryset_list, many=True)
#             #print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         elif type=='breed' and openid:
#             queryset_list = DogBreed.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogbreedListSerializer(queryset_list, many=True)
#             #print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         elif type=='adopt' and openid:
#             queryset_list = DogAdoption.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogadoptListSerializer(queryset_list, many=True)
#             #print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         elif type=='delivery' and openid:
#             queryset_list = DogDelivery.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogdeliverySerializer(queryset_list, many=True)
#             #print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         elif type=='sale' and openid:
#             queryset_list = DogSale.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogSaleSerializer(queryset_list, many=True)
#             #print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         elif type=='buy' and openid:
#             queryset_list = DogBuy.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogBuySerializer(queryset_list, many=True)
#             #print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         elif type=='institution' and openid:
#             queryset_list = Doginstitution.objects.filter(is_show=1).filter(openid=openid).order_by('-create_time')
#             serializer = DogInstitutionSerializer(queryset_list, many=True)
#             #print(serializer.data)
#             resp = {
#                 'results':serializer.data
#             }
#             return Response(resp)
#         else:
#             resp = {
#                 'results':[]
#             }
#             return Response(resp)
#
#
# class UpdateLossView(RetrieveUpdateAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = DogLossDetailSerializer
#     queryset = DogLoss.objects.all()
#
#
# class UpdateOwnerView(RetrieveUpdateAPIView):
#     permission_classes = [AllowAny]
#     serializer_class = DogOwnerDetailSerializer
#     queryset = DogOwner.objects.all()