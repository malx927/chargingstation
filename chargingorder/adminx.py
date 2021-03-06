# coding=utf-8
import decimal
import logging
from django.contrib import admin
from django.db.models import Q
from django.urls import reverse
from stationmanager.models import Station, ChargingPile
import xadmin
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper, AppendedText, Col, TabHolder, Tab
from .models import Order, OrderRecord, OrderChargDetail, ChargingOrder, Track, UnusualOrder, ParkingFeeOrder

CHARG_STATUS = 6    # 充电中编码


class ChargingOrderAdmin(object):
    list_display = [
        'out_trade_no', 'name', 'charg_mode', 'station_name', 'pile_name', 'gun_num', 'car_type', 'total_minutes', 'total_readings', 'begin_time',
        'consum_money', 'power_fee', 'service_fee', 'charg_status', 'curve'
    ]
    search_fields = ['out_trade_no', 'charg_pile__pile_sn', 'name', 'openid']
    list_filter = ['charg_status', 'begin_time', 'status']
    exclude = ['charg_type', 'station', 'seller', 'charg_pile']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    relfield_style = 'fk_ajax'
    refresh_times = [3, 5]  # 计时刷新
    # aggregate_fields = {"total_readings": "sum", 'cash_fee': "sum"}
    object_list_template = "chargingorder/order_model_list.html"

    form_layout = (
        Main(
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'name'),
                Row('seller_name', 'station_name'),
                Row('pile_name', 'gun_num'),
                Row('charg_mode', 'protocol'),
                Row('start_model', 'openid'),
                Row(
                    AppendedText('total_fee', '元'),
                    AppendedText('charg_min_val', '分钟'),
                ),
                Row(
                    AppendedText('charg_soc_val', '%'),
                    AppendedText('charg_reading_val', '度'),
                ),
            ),
            Fieldset(
                '充电信息',
                Row(
                    AppendedText('begin_soc', '%'),
                    AppendedText('end_soc', '%'),
                ),
                Row(
                    'begin_time',
                    'end_time',
                ),
                Row(
                    AppendedText('begin_reading', '度'),
                    AppendedText('end_reading', '度')
                ),
                Row(
                    AppendedText('total_readings', 'KWH'),
                    AppendedText('park_fee', '元'),
                ),
                Row(
                    AppendedText('power_fee', '元'),
                    AppendedText('service_fee', '元'),
                ),
            ),
            Fieldset(
                '支付情况',
                Row(
                    AppendedText('cash_fee', '元'),
                    AppendedText('consum_money', '元'),
                ),
                Row(
                    'transaction_id',
                    'pay_time',
                ),
                Row(
                    'balance',
                    'main_openid',
                ),
            ),
            Fieldset(
                '充电状态信息',
                 Row('charg_status', 'status'),
            ),
        ),
        Side(
            Fieldset(
                '车辆信息',
                'car_type',
                'vin_code',
                AppendedText('max_current', '安'),
                AppendedText('max_voltage', '伏'),
                AppendedText('max_single_voltage', '伏'),
                AppendedText('max_temp', '度'),
            ),
            Fieldset(
                '其他信息',
                'output_voltage',
                'output_current',
                'prev_reading',
                'start_charge_seq',
                'report_result',
                'report_time',
            ),
        ),

    )

    def queryset(self):
        queryset = super().queryset()

        if self.request.user.station:
            return queryset.filter(station=self.request.user.station, charg_status_id=CHARG_STATUS).exclude(status=2)
        elif self.request.user.seller:
            return queryset.filter(seller=self.request.user.seller, charg_status_id=CHARG_STATUS).exclude(status=2)
        else:
            return queryset.filter(charg_status_id=CHARG_STATUS).exclude(status=2)

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'charg_pile':
            if self.request.user.is_superuser:
                pass
            elif self.request.user.station:
                kwargs['queryset'] = ChargingPile.objects.filter(station=self.request.user.station)
            elif self.request.user.seller:
                kwargs['queryset'] = ChargingPile.objects.filter(station__seller=self.request.user.seller)
        return super().formfield_for_dbfield(db_field,  **kwargs)

    def has_add_permission(self):
        return False

    def has_change_permission(self, obj=None):
        return False

    def has_delete_permission(self, obj=None):
        return False

    def curve(self, obj):
        curve_url = reverse("order-detail-list", kwargs={"out_trade_no": obj.out_trade_no})
        refund_btn = "<a class='btn btn-xs btn-primary' data-toggle='modal' data-target='#myModal' " \
                     "data-uri='{}'>监控曲线</a>".format(curve_url)
        return refund_btn

    curve.short_description = "充电监控"
    curve.allow_tags = True
    curve.is_column = True


xadmin.site.register(ChargingOrder, ChargingOrderAdmin)


class UnusualOrderAdmin(object):
    list_display = [
        'out_trade_no', 'name', 'charg_mode', 'station_name', 'pile_name', 'gun_num', 'car_type', 'total_minutes', 'total_readings', 'begin_time',
        'consum_money', 'power_fee', 'service_fee', 'charg_status', 'curve'
    ]
    search_fields = ['out_trade_no', 'charg_pile__pile_sn', 'name', 'openid']
    list_filter = ['charg_status', 'begin_time', 'status']
    exclude = ['charg_type', 'seller', 'station', 'charg_pile']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    relfield_style = 'fk_ajax'
    object_list_template = "chargingorder/order_model_list.html"

    form_layout = (
        Main(
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'name'),
                Row('seller_name', 'station_name'),
                Row('pile_name', 'gun_num'),
                Row('charg_mode', 'protocol'),
                Row('start_model', 'openid'),
                Row(
                    AppendedText('total_fee', '元'),
                    AppendedText('charg_min_val', '分钟'),
                ),
                Row(
                    AppendedText('charg_soc_val', '%'),
                    AppendedText('charg_reading_val', '度'),
                ),
            ),
            Fieldset(
                '充电信息',
                Row(
                    AppendedText('begin_soc', '%'),
                    AppendedText('end_soc', '%'),
                ),
                Row(
                    'begin_time',
                    'end_time',
                ),
                Row(
                    AppendedText('begin_reading', '度'),
                    AppendedText('end_reading', '度')
                ),
                Row(
                    AppendedText('total_readings', 'KWH'),
                    AppendedText('park_fee', '元'),
                ),
                Row(
                    AppendedText('power_fee', '元'),
                    AppendedText('service_fee', '元'),
                ),
            ),
            Fieldset(
                '支付情况',
                Row(
                    AppendedText('cash_fee', '元'),
                    AppendedText('consum_money', '元'),
                ),
                Row(
                    'transaction_id',
                    'pay_time',
                ),
                Row(
                    'balance',
                    'main_openid',
                ),
            ),
            Fieldset(
                '充电状态信息',
                 Row('charg_status', 'status'),
            ),
        ),
        Side(
            Fieldset(
                '车辆信息',
                'car_type',
                'vin_code',
                AppendedText('max_current', '安'),
                AppendedText('max_voltage', '伏'),
                AppendedText('max_single_voltage', '伏'),
                AppendedText('max_temp', '度'),
            ),
            Fieldset(
                '其他信息',
                'output_voltage',
                'output_current',
                'prev_reading',
                'start_charge_seq',
                'report_result',
                'report_time',
            ),
        ),

    )

    def queryset(self):
        queryset = super().queryset()

        if self.request.user.station:
            return queryset.filter(station=self.request.user.station).filter(Q(total_readings=0) & Q(status=2) | Q(charg_status__fault=1))
        elif self.request.user.seller:
            return queryset.filter(seller=self.request.user.seller).filter(Q(total_readings=0) & Q(status=2) | Q(charg_status__fault=1))
        else:
            return queryset.filter(Q(total_readings=0) & Q(status=2) | Q(charg_status__fault=1))

    def has_add_permission(self):
        return False

    def has_change_permission(self, obj=None):
        return False

    def has_delete_permission(self, obj=None):
        return False

    def curve(self, obj):
        curve_url = reverse("order-detail-list", kwargs={"out_trade_no": obj.out_trade_no})
        refund_btn = "<a class='btn btn-xs btn-primary' data-toggle='modal' data-target='#myModal' " \
                     "data-uri='{}'>监控曲线</a>".format(curve_url)
        return refund_btn

    curve.short_description = "充电监控"
    curve.allow_tags = True
    curve.is_column = True


xadmin.site.register(UnusualOrder, UnusualOrderAdmin)


# 订单admin
class OrderAdmin(object):
    list_display = [
        'out_trade_no', 'name', 'charg_mode', 'station_name', 'pile_name', 'gun_num', 'car_type', 'total_minutes', 'total_readings', 'begin_time', 'pay_time',
        'consum_money', 'power_fee', 'service_fee', 'cash_fee', 'charg_status', 'status', 'report_result', 'curve'
    ]
    search_fields = ['out_trade_no', 'charg_pile__pile_sn', 'name', 'openid', 'car_type']
    list_filter = ['seller', 'station', 'charg_pile', 'charg_mode', 'charg_status', 'begin_time', 'status', 'report_result']
    exclude = ['charg_type', 'seller', 'station', 'charg_pile']
    date_hierarchy = 'begin_time'
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    readonly_fields = ["balance", "main_openid"]
    relfield_style = 'fk_ajax'
    aggregate_fields = {"total_readings": "sum", 'consum_money': "sum", 'cash_fee': "sum",  'power_fee': "sum", "service_fee": "sum"}
    object_list_template = "chargingorder/order_model_list.html"

    form_layout = (
        Main(
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'name'),
                Row('seller_name', 'station_name'),
                Row('pile_name', 'gun_num'),
                Row('charg_mode', 'protocol'),
                Row('start_model', 'openid'),
                Row(
                    AppendedText('total_fee', '元'),
                    AppendedText('charg_min_val', '分钟'),
                ),
                Row(
                    AppendedText('charg_soc_val', '%'),
                    AppendedText('charg_reading_val', '度'),
                ),
            ),
            Fieldset(
                '充电信息',
                Row(
                    AppendedText('begin_soc', '%'),
                    AppendedText('end_soc', '%'),
                ),
                Row(
                    'begin_time',
                    'end_time',
                ),
                Row(
                    AppendedText('begin_reading', '度'),
                    AppendedText('end_reading', '度')
                ),
                Row(
                    AppendedText('total_readings', 'KWH'),
                    AppendedText('park_fee', '元'),
                ),
                Row(
                    AppendedText('power_fee', '元'),
                    AppendedText('service_fee', '元'),
                ),
            ),
            Fieldset(
                '支付情况',
                Row(
                    AppendedText('cash_fee', '元'),
                    AppendedText('consum_money', '元'),
                ),
                Row(
                    'transaction_id',
                    'pay_time',
                ),
                Row(
                    'balance',
                    'main_openid',
                ),
            ),
            Fieldset(
                '充电状态信息',
                 Row('charg_status', 'status'),
            ),
        ),
        Side(
            Fieldset(
                '车辆信息',
                'car_type',
                'vin_code',
                AppendedText('max_current', '安'),
                AppendedText('max_voltage', '伏'),
                AppendedText('max_single_voltage', '伏'),
                AppendedText('max_temp', '度'),
            ),
            Fieldset(
                '其他信息',
                'output_voltage',
                'output_current',
                'prev_reading',
                'start_charge_seq',
                'report_result',
                'report_time',
            ),
        ),

    )

    def curve(self, obj):
        curve_url = reverse("order-detail-list", kwargs={"out_trade_no": obj.out_trade_no})
        refund_btn = "<a class='btn btn-xs btn-primary' data-toggle='modal' data-target='#myModal' " \
                     "data-uri='{}'>监控曲线</a>".format(curve_url)
        return refund_btn

    curve.short_description = "充电监控"
    curve.allow_tags = True
    curve.is_column = True

    def queryset(self):
        queryset = super(OrderAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(seller=self.request.user.seller)
        else:
            return queryset

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'charg_pile':
            if self.request.user.is_superuser:
                pass
            elif self.request.user.station:
                kwargs['queryset'] = ChargingPile.objects.filter(station=self.request.user.station)
            elif self.request.user.seller:
                kwargs['queryset'] = ChargingPile.objects.filter(station__seller=self.request.user.seller)
        return super(OrderAdmin, self).formfield_for_dbfield(db_field,  **kwargs)

    def get_media(self):
        media = super(OrderAdmin, self).get_media()
        # path = self.request.get_full_path()
        # if "add" in path or 'update' in path:
        media.add_js([self.static('stationmanager/js/xadmin.areacode.js')])
        return media


xadmin.site.register(Order, OrderAdmin)


# 订单明细记录
class OrderRecordAdmin(object):

    def charg_time(self, obj):
        if obj.begin_time is None or obj.end_time is None:
            return 0
        else:
            # return int((obj.end_time - obj.begin_time).seconds / 60)
            mins = decimal.Decimal((obj.end_time - obj.begin_time).total_seconds() / 60)
            return mins.quantize(decimal.Decimal('0.01'))

    charg_time.short_description = '充电时间(分)'
    charg_time.allow_tags = True
    charg_time.is_column = True

    def meter_quantity(self, obj):
        return obj.end_reading - obj.begin_reading
    meter_quantity.short_description = '充电电量(度)'
    meter_quantity.allow_tags = True
    meter_quantity.is_column = True

    def power_money(self, obj):
        return ((obj.end_reading - obj.begin_reading) * obj.price).quantize(decimal.Decimal("0.01"))
    power_money.short_description = '电费金额(元)'
    power_money.allow_tags = True
    power_money.is_column = True

    def service_money(self, obj):
        return ((obj.end_reading - obj.begin_reading) * obj.service_price).quantize(decimal.Decimal("0.01"))
    service_money.short_description = '服务费金额(元)'
    service_money.allow_tags = True
    service_money.is_column = True

    list_display = ['out_trade_no', 'pile_sn', 'gun_num', 'charg_time', 'meter_quantity', 'price', 'service_price', 'accumulated_readings', 'accumulated_amount', 'accumulated_service_amount']
    search_fields = ['out_trade_no']
    exclude = ["price_begin_time", "price_end_time", "order"]
    readonly_fields = ['charg_time', 'meter_quantity', 'accumulated_service_amount', 'accumulated_readings', 'accumulated_amount']
    date_hierarchy = 'begin_time'
    list_per_page = 30
    model_icon = 'fa fa-file-text'

    form_layout = (
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'pile_sn'),
                Row('serial_num', None),
                Row('gun_num', "current_soc"),
            ),
            Fieldset(
                '充电信息',
                Row('begin_time', AppendedText('begin_reading', '度'),),
                Row('end_time', AppendedText('end_reading', '度'),),
                Row(AppendedText('price', '元/度'), AppendedText('service_price', '元/度')),
                Row('charg_time', 'meter_quantity', 'accumulated_readings', 'accumulated_amount', 'accumulated_service_amount'),
            ),

    )

    def queryset(self):
        queryset = super(OrderRecordAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(station_id=self.request.user.station_id)
        elif self.request.user.seller:
            return queryset.filter(seller_id=self.request.user.seller_id)
        else:
            return queryset

    # def formfield_for_dbfield(self, db_field,  **kwargs):
    #     if db_field.name == 'order':
    #         if self.request.user.is_superuser:
    #             pass
    #         elif self.request.user.station:
    #             kwargs['queryset'] = Order.objects.filter(charg_pile__station=self.request.user.station)
    #         elif self.request.user.seller:
    #             kwargs['queryset'] = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)
    #     return super(OrderRecordAdmin, self).formfield_for_dbfield(db_field,  **kwargs)


xadmin.site.register(OrderRecord, OrderRecordAdmin)


class OrderChargDetailAdmin(object):
    list_display = ['pile_sn', 'gun_num', 'out_trade_no', 'current_time', 'current_soc', 'current_reading', 'prev_reading',
                    'voltage', 'current', 'output_voltage', 'output_current', 'update_time']
    search_fields = ['out_trade_no', 'pile_sn']
    list_per_page = 50
    model_icon = 'fa fa-file-text'


xadmin.site.register(OrderChargDetail, OrderChargDetailAdmin)


# 占位费订单
class ParkingFeeOrderAdmin(object):
    list_display = [
        'out_trade_no', 'name', 'station_name', 'pile_name', 'gun_num', 'begin_time', 'end_time', 'park_fee', 'status']
    search_fields = ['out_trade_no', 'charg_pile__pile_sn', 'name', 'openid']
    list_filter = ['seller', 'station', 'charg_pile', 'begin_time', 'status']
    exclude = ['seller', 'station', 'charg_pile']

    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    readonly_fields = ["balance"]
    relfield_style = 'fk_ajax'

    form_layout = (
        Main(
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'name'),
                Row('seller_name', 'station_name'),
                Row('pile_name', 'gun_num'),
                Row(
                    'openid',
                    AppendedText('park_fee', '元'),
                    ),
                Row(
                    'begin_time',
                    'end_time',
                ),
                Row(
                    'balance',
                    'status',
                ),
            ),

        ),
    )

    def queryset(self):
        queryset = super(ParkingFeeOrderAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(seller=self.request.user.seller)
        else:
            return queryset

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'charg_pile':
            if self.request.user.is_superuser:
                pass
            elif self.request.user.station:
                kwargs['queryset'] = ChargingPile.objects.filter(station=self.request.user.station)
            elif self.request.user.seller:
                kwargs['queryset'] = ChargingPile.objects.filter(station__seller=self.request.user.seller)
        return super(ParkingFeeOrderAdmin, self).formfield_for_dbfield(db_field,  **kwargs)


xadmin.site.register(ParkingFeeOrder, ParkingFeeOrderAdmin)


class TrackAdmin(object):
    list_display = ['out_trade_no', 'oper_name', 'oper_user', 'oper_time', 'comments']
    search_fields = ['out_trade_no']
    list_per_page = 50
    model_icon = 'fa fa-file-text'


xadmin.site.register(Track, TrackAdmin)