# coding=utf-8
from django.shortcuts import render
from django.views import View

from wxchat.views import getJsApiSign
from .models import ChargingPile, Station, ChargingPrice


class StationListView(View):
    """充电站列表"""
    def get(self, request, *arg, **kwargs):
        sign = getJsApiSign(request)
        stations = Station.objects.all()
        context = {
            "sign": sign,
            "stations": stations,
        }
        print(request.session.get("openid"))
        return render(request, template_name='weixin/station_index.html', context=context)


class StationDetailView(View):
    """电站详情"""
    def get(self, request, *args, **kwargs):
        sign = getJsApiSign(request)
        station_id = kwargs.get("stationid")
        try:
            station = Station.objects.get(id=station_id)
        except Station.DoesNotExist as ex:
            station = None

        # print(station.get_gun_totals_by_type())
        # print(station.get_gun_totals_by_status())

        context = {
            "sign": sign,
            "station": station,
        }
        return render(request, template_name='weixin/station_detail.html', context=context)


class StationPricesDetailView(View):
    def get(self, request, *args, **kwargs):
        station_id = kwargs.get("stationid", None)
        price_details = None
        if station_id:
            try:
                charg_price = ChargingPrice.objects.get(station_id=station_id, default_flag=1)
                price_details = charg_price.prices.all()
            except ChargingPrice.DoesNotExist as ex:
                print("StationPricesDetailView:", ex)

        context = {
            "price_details": price_details,
        }
        return render(request, template_name="weixin/stage_price.html", context=context)


# class DashboardListView(View):
#     def get(self, request, *args, **kwargs):
#         station_id = request.GET.get("station_id", None)
#
#         if pile_sn and gun_num:
#             return render(request, template_name='stationmanager/recharge.html', context={"pile_sn": pile_sn})
#         else:
#             piles = ChargingPile.objects.all()
#             return render(request, template_name='stationmanager/index.html', context={"piles": piles})
