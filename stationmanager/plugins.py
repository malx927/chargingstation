# coding=utf-8
from django.db.models import Q, Sum, Count, FloatField, F
from django.template import loader
from chargingorder.models import Order
from xadmin.plugins.utils import get_context_dict
import datetime
__author__ = 'Administrator'

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, Dashboard


class DashBoardPlugin(BaseAdminPlugin):
    is_dashboard = False

    def init_request(self, *args, **kwargs):
        if self.request.get_full_path() == '/ydadmin/':
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

        today_results = Order.objects.select_related("charg_pile").filter(status=2, begin_time__date=curr_date).values(
            station_id=F("charg_pile__station"), station_name=F("charg_pile__station__name")) \
            .annotate(total_readings=Sum("total_readings", output_field=FloatField()), counts=Count("id"),
                      total_fees=Sum("consum_money", output_field=FloatField()),
                      times=Sum((F("end_time") - F("begin_time")) / (1000000 * 60))).order_by("station_id")

        context.update({'today_results': today_results})
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




