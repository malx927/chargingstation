# coding=utf-8
import decimal
import logging
from django.contrib import admin
from stationmanager.models import Station, ChargingPile
import xadmin
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper, AppendedText, Col, TabHolder, Tab
from .models import Order, OrderRecord, OrderChargDetail


# 订单admin
class OrderAdmin(object):
    list_display = [
        'out_trade_no', 'name', 'charg_mode', 'station', 'charg_pile', 'gun_num', 'total_minutes', 'total_readings', 'begin_time', 'pay_time',
        'consum_money', 'power_fee', 'service_fee', 'cash_fee', 'status', 'report_result'
    ]
    search_fields = ['out_trade_no', 'charg_pile__pile_sn', 'name', 'openid']
    list_filter = ['charg_pile', 'charg_mode', 'charg_status', 'begin_time', 'status', 'report_result']
    exclude = ['charg_type']
    date_hierarchy = 'begin_time'
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    readonly_fields = ["balance", "main_openid"]
    relfield_style = 'fk_ajax'
    aggregate_fields = {"total_readings": "sum", 'consum_money': "sum", 'cash_fee': "sum",  'power_fee': "sum", "service_fee": "sum"}

    form_layout = (
        Main(
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'name'),
                Row('charg_pile', 'gun_num'),
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

    def station(self, obj):
        return obj.charg_pile.station.name
    station.short_description = '充电站'
    station.allow_tags = True
    station.is_column = True

    def queryset(self):
        queryset = super(OrderAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(charg_pile__station__seller=self.request.user.seller)
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

    list_display = ['out_trade_no', 'pile_sn', 'gun_num', 'charg_time', 'meter_quantity', 'price', 'power_money', 'service_price', 'service_money',
                    'accumulated_readings', 'accumulated_amount', 'accumulated_service_amount']
    search_fields = ['order__out_trade_no']
    exclude = ["price_begin_time", "price_end_time"]
    readonly_fields = ['charg_time', 'meter_quantity', 'power_money', 'service_money', 'accumulated_service_amount', 'accumulated_readings', 'accumulated_amount']
    list_filter = ['begin_time', 'order']
    date_hierarchy = 'begin_time'
    list_per_page = 30
    model_icon = 'fa fa-file-text'

    form_layout = (
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'pile_sn'),
                Row('order', 'serial_num'),
                Row('gun_num', "current_soc"),
            ),
            Fieldset(
                '充电信息',
                Row('begin_time', AppendedText('begin_reading', '度'),),
                Row('end_time', AppendedText('end_reading', '度'),),
                Row(AppendedText('price', '元/度'), AppendedText('service_price', '元/度')),
                Row('meter_quantity', 'power_money', 'service_money'),
                Row('accumulated_readings', 'accumulated_amount', 'accumulated_service_amount'),

            ),

    )

    def queryset(self):
        queryset = super(OrderRecordAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(order__charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(order__charg_pile__station__seller=self.request.user.seller)
        else:
            return queryset

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'order':
            if self.request.user.is_superuser:
                pass
            elif self.request.user.station:
                kwargs['queryset'] = Order.objects.filter(charg_pile__station=self.request.user.station)
            elif self.request.user.seller:
                kwargs['queryset'] = Order.objects.filter(charg_pile__station__seller=self.request.user.seller)
        return super(OrderRecordAdmin, self).formfield_for_dbfield(db_field,  **kwargs)


xadmin.site.register(OrderRecord, OrderRecordAdmin)


class OrderChargDetailAdmin(object):
    list_display = ['pile_sn', 'gun_num', 'out_trade_no', 'current_time', 'current_soc', 'current_reading', 'prev_reading',
                    'voltage', 'current', 'output_voltage', 'output_current', 'update_time']
    search_fields = ['out_trade_no', 'pile_sn']
    list_per_page = 50
    model_icon = 'fa fa-file-text'


xadmin.site.register(OrderChargDetail, OrderChargDetailAdmin)
