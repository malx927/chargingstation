#-*-coding:utf-8-*-
import datetime

from django.db.models import Sum, Count, Q, F, DecimalField, FloatField, IntegerField
from django.db import connection
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from chargingorder.models import Order
from stationmanager.models import ChargingPile, Station, Seller

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

        if self.request.user.is_superuser:
            queryset = Order.objects.all()
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.none()

        if flag is None:    # 当天
            cur_time = datetime.datetime.now().date()
            results = queryset.filter(begin_time__date=cur_time)\
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                           times=Sum((F("end_time") - F("begin_time"))/(1000000 * 60 * 60), output_field=DecimalField(decimal_places=2)))
        elif flag == "1":   # 昨天
            yesterday = datetime.datetime.now() + datetime.timedelta(days=-1)
            yesterday = yesterday.date()
            results = queryset.filter(status=2, begin_time__date=yesterday) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2)))
        elif flag == "2":   # 任意天
            sdate = request.GET.get("sdate", None)
            if sdate:
                search_date = datetime.datetime.strptime(sdate, "%Y-%m-%d")
                s_date = search_date.date()
                results = queryset.filter(status=2, begin_time__date=s_date) \
                    .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                               times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2)))
        results["readings"] = 0.00 if results["readings"] is None else results["readings"]
        results["total_fees"] = 0.00 if results["total_fees"] is None else results["total_fees"]
        results["times"] = 0.00 if results["times"] is None else results["times"]
        return Response(results)


class OrderMonthStats(APIView):
    """月统计"""
    def get(self, request, *args, **kwargs):
        month = request.GET.get("month", None)
        if self.request.user.is_superuser:
            queryset = Order.objects.all()
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.none()

        if month is None:  # 当月
            cur_time = datetime.datetime.now()
            results = queryset.filter(begin_time__year=cur_time.year, begin_time__month=cur_time.month) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2)))
        else:  # 任意月
            s_date = datetime.datetime.strptime(month, "%Y-%m")
            results = queryset.filter(begin_time__year=s_date.year, begin_time__month=s_date.month) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2)))

        results["readings"] = 0.00 if results["readings"] is None else results["readings"]
        results["total_fees"] = 0.00 if results["total_fees"] is None else results["total_fees"]
        results["times"] = 0.00 if results["times"] is None else results["times"]
        return Response(results)


class OrderYearStats(APIView):
    """年统计"""
    def get(self, request, *args, **kwargs):
        year = request.GET.get("year", None)
        if self.request.user.is_superuser:
            queryset = Order.objects.all()
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)
        else:
            queryset = Order.objects.none()

        if year is None:  # 当年
            cur_time = datetime.datetime.now()
            results = queryset.filter(status=2, begin_time__year=cur_time.year) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2)))
        else:  # 任意年

            results = queryset.filter(status=2, begin_time__year=int(year)) \
                .aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                           times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60), output_field=DecimalField(decimal_places=2)))

        results["readings"] = 0.00 if results["readings"] is None else results["readings"]
        results["total_fees"] = 0.00 if results["total_fees"] is None else results["total_fees"]
        results["times"] = 0.00 if results["times"] is None else results["times"]
        return Response(results)


class OrderCategoryStats(APIView):
    """分类统计"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        begin_time = request.GET.get("begin_time", None)
        end_time = request.GET.get("end_time", None)
        print("category=", category)
        if category is None or category == "":
            category = "1"
        if self.request.user.is_superuser:
            queryset = Order.objects.all()
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)

        if begin_time and end_time:
            b_date = datetime.datetime.strptime(begin_time, "%Y-%m-%d")
            e_date = datetime.datetime.strptime(end_time, "%Y-%m-%d")
            queryset = queryset.filter(status=2, begin_time__date__range=[b_date, e_date])
        else:
            queryset = queryset.filter(status=2)

        if category == "1":     # 按运营商统计
            result = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name").order_by("charg_pile__station__seller").\
                annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                         times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
        elif category == "2":     # 按充电站统计
            result = queryset.values("charg_pile__station__seller__name", "charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station"). \
                            annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                                     times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
        elif category == "3":     # 按充电桩统计
            result = queryset.values("charg_pile", "charg_pile__name", "charg_pile__station__seller__name", "charg_pile__station__name")\
                            .order_by("charg_pile"). \
                            annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"),
                                     times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))

        return Response(result)


class OrderDayAnalysis(APIView):
    """日统计分析"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        s_date = request.GET.get("s_date", None)

        if category is None or category == "":
            category = "1"
        if self.request.user.is_superuser:
            queryset = Order.objects.all()
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)

        if s_date:
            d_date = datetime.datetime.strptime(s_date, "%Y-%m-%d")
            queryset = queryset.filter(status=2, begin_time__date=d_date)
        else:
            queryset = queryset.filter(status=2, )

        if category == "1":     # 按运营商统计
            results = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name")\
                            .order_by("charg_pile__station__seller")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results
        elif category == "2":     # 按充电站统计
            results = queryset.values("charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results
        elif category == "3":     # 按充电桩统计
            results = queryset.values("charg_pile", "charg_pile__name")\
                            .order_by("charg_pile")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results

        return Response(totals)


class OrderMonthAnalysis(APIView):
    """月统计分析"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        s_month = request.GET.get("s_month", None)

        if category is None or category == "":
            category = "1"
        if self.request.user.is_superuser:
            queryset = Order.objects.all()
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)

        if s_month:
            d_date = datetime.datetime.strptime(s_month, "%Y-%m")
            queryset = queryset.filter(status=2, begin_time__year=d_date.year, begin_time__month=d_date.month)
        else:
            queryset = queryset.filter(status=2)

        if category == "1":     # 按运营商统计
            results = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name")\
                            .order_by("charg_pile__station__seller")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results
        elif category == "2":     # 按充电站统计
            results = queryset.values("charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results
        elif category == "3":     # 按充电桩统计
            results = queryset.values("charg_pile", "charg_pile__name")\
                            .order_by("charg_pile")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results

        return Response(totals)


class OrderYearAnalysis(APIView):
    """年统计分析"""
    def get(self, request, *args, **kwargs):
        category = request.GET.get("category", None)
        s_year = request.GET.get("s_year", None)

        if category is None or category == "":
            category = "1"
        if self.request.user.is_superuser:
            queryset = Order.objects.all()
        elif self.request.user.station:
            queryset = Order.objects.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            queryset = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)

        if s_year:
            d_date = datetime.datetime.strptime(s_year, "%Y")
            queryset = queryset.filter(status=2, begin_time__year=d_date.year)
        else:
            queryset = queryset.filter(status=2)

        if category == "1":     # 按运营商统计
            results = queryset.values("charg_pile__station__seller", "charg_pile__station__seller__name")\
                            .order_by("charg_pile__station__seller")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results
        elif category == "2":     # 按充电站统计
            results = queryset.values("charg_pile__station", "charg_pile__station__name")\
                            .order_by("charg_pile__station")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results
        elif category == "3":     # 按充电桩统计
            results = queryset.values("charg_pile", "charg_pile__name")\
                            .order_by("charg_pile")\
                            .annotate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals = queryset.aggregate(readings=Sum("total_readings"), counts=Count("id"), total_fees=Sum("consum_money"), times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60 * 60)))
            totals["results"] = results

        return Response(totals)

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