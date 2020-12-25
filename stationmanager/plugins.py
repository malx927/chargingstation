# coding=utf-8
from django.db.models import Q, Sum, Count, FloatField, F
from django.template import loader
from chargingorder.models import Order
from stationmanager.models import Station
from xadmin.plugins.utils import get_context_dict
import datetime
__author__ = 'Administrator'

from xadmin.views import BaseAdminPlugin, Dashboard


class DashBoardPlugin(BaseAdminPlugin):
    is_dashboard = False

    def init_request(self, *args, **kwargs):
        if self.request.get_full_path() == '/ydadmin/' or self.request.get_full_path() == '/ydlogin/':
            self.is_dashboard = True
        return bool(self.is_dashboard)

    def get_context(self, context):
        # if self.request.user.is_superuser:
        #     stations = Station.objects.all()
        #     fault_guns = ChargingGun.objects.filter(Q(work_status=2) | Q(work_status=9))
        # elif self.request.user.station:
        #     stations = Station.objects.filter(id=self.request.user.station.id)
        #     fault_guns = ChargingGun.objects.filter(Q(work_status=2) | Q(work_status=9), charg_pile__station=self.request.user.station)
        # elif self.request.user.seller:
        #     stations = Station.objects.filter(seller=self.request.user.seller)
        #     fault_guns = ChargingGun.objects.filter(Q(work_status=2) | Q(work_status=9), charg_pile__station__seller=self.uest.user.seller)
        # else:
        #     stations = None
        #     fault_guns = None
        #
        # context.update({'stations': stations})
        # context.update({'fault_guns': fault_guns})
        curr_date = datetime.datetime.now().date()
        orders = Order.objects.filter(begin_time__date=curr_date)
        stations = Station.objects.all()
        if self.request.user.is_superuser:
            pass
        elif self.request.user.station:
            orders = orders.filter(charg_pile__station=self.request.user.station)
            stations = stations.filter(id=self.request.user.station.id)
        elif self.request.user.seller:
            orders = orders.filter(charg_pile__station__seller=self.request.user.seller)
            stations = stations.filter(seller=self.request.user.seller)

        today_results = orders.values(station_id=F("charg_pile__station"), station_name=F("charg_pile__station__name")) \
            .annotate(
                total_readings=Sum("total_readings", output_field=FloatField()),
                counts=Count("id"),
                total_fees=Sum("consum_money", output_field=FloatField()),
                service_fees=Sum("service_fee"),
                times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60))
            ).order_by("station_id")

        stations = stations.values("id", "name")

        stations_list = list(stations)
        for station in stations_list:
            station["total_readings"] = 0
            station["counts"] = 0
            station["total_fees"] = 0
            station["times"] = 0
            station["service_fees"] = 0
            for result in today_results:
                if result["station_id"] == station["id"]:
                    station["total_readings"] = result.get("total_readings", 0)
                    station["counts"] = result.get("counts", 0)
                    station["total_fees"] = result.get("total_fees", 0)
                    station["times"] = result.get("times", 0)
                    station["service_fees"] = result.get("service_fees", 0)

        # print(stations_list)
        context.update({'stations_list': stations_list})
        return context

    def block_results_top(self, context, nodes):
        if self.is_dashboard:
            nodes.append(
                loader.render_to_string('stationmanager/dashboard.model_list.html', context=get_context_dict(context))
            )

        # Media
    def get_media(self, media):
        media.add_css({'screen': [self.static('stationmanager/css/dashboard.css'), ]})
        media.add_css({'screen': [self.static('xadmin/vendor/bootstrap-datepicker/css/datepicker.css'), ]})
        media.add_css({'screen': [self.static('xadmin/vendor/select2/select2.css'), ]})
        media.add_css({'screen': [self.static('xadmin/vendor/selectize/selectize.css'), ]})
        media.add_css({'screen': [self.static('xadmin/vendor/selectize/selectize.bootstrap3.css'), ]})
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/bootstrap-datepicker.js')])
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/locales/bootstrap-datepicker.zh-CN.js')])
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/locales/bootstrap-datepicker.zh-CN.js')])
        media.add_js([self.static('statistic/js/echarts.min.js')])
        media.add_js([self.static('statistic/js/china.js')])
        return media


class WarningPlugin(BaseAdminPlugin):
    is_warning = False

    def init_request(self, *args, **kwargs):
        self.is_warning = True
        return bool(self.is_warning)

    def block_top_navbar(self, context, nodes):
        if self.is_warning:
            nodes.append(
                loader.render_to_string('stationmanager/charging_pile_warning.html', context=get_context_dict(context))
            )




