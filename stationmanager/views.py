# coding=utf-8
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
import logging

from chargingorder.models import Order
from wxchat.decorators import weixin_decorator
from wxchat.models import UserInfo
from wxchat.views import getJsApiSign
from .models import ChargingPile, Station, ChargingPrice, FaultChargingGun

logger = logging.getLogger("django")


class StationListView(View):
    """充电站列表"""
    # @method_decorator(weixin_decorator)
    def get(self, request, *arg, **kwargs):
        # sign = getJsApiSign(request)
        context = {
            # "sign": sign,
        }
        openid = request.session.get("openid", None)
        user = UserInfo.objects.filter(openid=openid).first()
        if user:
            order = Order.objects.filter(out_trade_no=user.out_trade_no, charg_status_id__gt=0, charg_status_id__lt=7).first()
            if order:
                context["order"] = order

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
                logger.info(ex)

        context = {
            "price_details": price_details,
        }
        return render(request, template_name="weixin/stage_price.html", context=context)


class FaultChargingGunListView(View):
    def get(self, request, *args, **kwargs):
        fault_counts = FaultChargingGun.objects.filter(repair_flag=False).count()
        data = {
            "fault_counts": fault_counts
        }
        return JsonResponse(data)
