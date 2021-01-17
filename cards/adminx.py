# coding=utf-8
import xadmin
from cards.models import ChargingCard, CardRecharge, CardOrder
from stationmanager.models import ChargingPile, Station, Seller
from xadmin.layout import Fieldset, Row, AppendedText, Main, Side


# class CardUserAdmin(object):
#     """储值卡用户"""
#     list_display = ['name', 'password', 'telephone', 'address', 'bank', 'account', 'is_active', 'add_time']
#     search_fields = ['name', 'telephone', 'address', 'bank', 'account']
#     list_per_page = 50
#     model_icon = 'fa fa-file-text'
#     show_all_rel_details = False


# xadmin.site.register(CardUser, CardUserAdmin)


class ChargingCardAdmin(object):
    """储值卡"""
    list_display = ['card_num', 'face_num', 'name', 'seller', 'station', 'telephone', 'money', 'status', 'add_time', 'startup']
    search_fields = ['face_num', 'card_num', 'telephone', 'name']
    list_filter = ['status', 'seller', 'station']
    list_per_page = 50
    exclude = ['sec_num', 'cipher', 'pile_sn', 'gun_num']
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    readonly_fields = ["money"]
    object_list_template = "cards/cards_model_list.html"

    form_layout = (
        Fieldset(
            '储值卡信息',
            Row('card_num', 'seller'),
            Row('station', 'status'),
            Row('name', 'telephone'),
            Row('money', None),
        ),
        Fieldset(
            '有效期限',
            'is_valid_date',
            Row('start_date', "end_date"),
        ),
    )

    def get_form_layout(self):
        if self.request.user.is_oper_mgr or self.request.user.is_superuser:
            self.form_layout = None

        return super().get_form_layout()

    def get_list_display(self):
        if self.request.user.is_oper_mgr or self.request.user.is_superuser:
            self.list_display =  ['card_num', 'face_num', 'name', 'seller', 'station', 'telephone', 'money', 'status', 'add_time']
        return super().get_list_display()

    # def get_readonly_fields(self):
    #     if self.request.user.is_oper_mgr or self.request.user.is_superuser:
    #         self.readonly_fields = ['card_num', 'name', 'seller', 'station', 'telephone', 'money', 'status', 'is_valid_date', 'start_date', 'end_date']
    #     return self.readonly_fields

    def get_media(self):
        media = super(ChargingCardAdmin, self).get_media()
        path = self.request.get_full_path()
        if "add" not in path and 'update' not in path:
            media += self.vendor('xadmin.plugin.details.js', 'xadmin.form.css')
            # media.add_js([self.static('stationmanager/js/xadmin.areacode.js')])
        return media

    def has_add_permission(self):
        if self.request.user.is_oper_mgr:
            return False
        return True

    def has_change_permission(self, obj=None):
        if self.request.user.is_oper_mgr:
            return False
        return True

    def has_delete_permission(self, obj=None):
        if self.request.user.is_oper_mgr:
            return False
        return True

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'seller':
            if self.request.user.is_superuser:
                pass
            elif self.request.user.station:
                kwargs['queryset'] = Seller.objects.filter(id=self.request.user.station.seller_id)
            elif self.request.user.seller:
                kwargs['queryset'] = Seller.objects.filter(id=self.request.user.seller_id)

        if db_field.name == 'station':
            if self.request.user.is_superuser:
                pass
            elif self.request.user.station:
                kwargs['queryset'] = Station.objects.filter(id=self.request.user.station.id)
            elif self.request.user.seller:
                kwargs['queryset'] = Station.objects.filter(seller=self.request.user.seller)

        return super().formfield_for_dbfield(db_field,  **kwargs)

    def save_models(self):
        obj = self.new_obj
        request = self.request
        if obj.seller is None:
            obj.seller = request.user.seller
        super().save_models()

    def queryset(self):
        queryset = super().queryset()
        if self.request.user.station:
            return queryset.filter(station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(seller=self.request.user.seller)
        else:
            return queryset
    # xadmin filter.py RelatedFieldListFilter
    # 增加条件过滤
    # if hasattr(model_admin, '{field}_choices'.format(field=field.name)):
    #     self.lookup_choices = getattr(model_admin, '{field}_choices'.format(field=field.name))(field, request,
    #                                                                                            params, model,
    #                                                                                            model_admin,
    #                                                                                            field_path)
    # else:
    #     self.lookup_choices = field.get_choices(include_blank=False)

    def seller_choices(self, field, request, params, model, model_admin, field_path):
        # print(field, params, model, model_admin, field_path)
        if self.request.user.station:
            seller_lst = Seller.objects.filter(id=self.request.user.station.seller.id).values("id", "name")
        elif self.request.user.seller:
            seller_lst = Seller.objects.filter(id=self.request.user.seller.id).values("id", "name")
        else:
            return field.get_choices(include_blank=False)
        print(seller_lst)
        # 返回格式 [('pk','标题'),]
        return list(((seller.get('id'), seller.get('name')) for seller in seller_lst))

    def station_choices(self, field, request, params, model, model_admin, field_path):
        # print(field, params, model, model_admin, field_path)
        if self.request.user.station:
            stations = Station.objects.filter(id=self.request.user.station.id).values("id", "name")
        elif self.request.user.seller:
            stations = Station.objects.filter(seller_id=self.request.user.seller.id).values("id", "name")
        else:
            return field.get_choices(include_blank=False)
        print(stations)

        return list(((station.get('id'), station.get('name')) for station in stations))


xadmin.site.register(ChargingCard, ChargingCardAdmin)


class CardRechargeAdmin(object):
    """储值卡充值"""
    list_display = ['seller', 'card', 'face_num', 'name', 'money', 'op_user', 'add_time']
    search_fields = ['card', 'face_num', 'name']
    list_filter = ['seller']
    # readonly_fields = ['card', 'money', 'op_user', 'seller']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False

    def has_add_permission(self):
        if self.request.user.is_superuser or self.request.user.is_oper_mgr:
            return False
        return False

    def has_change_permission(self, obj=None):
        if self.request.user.is_superuser or self.request.user.is_oper_mgr:
            return False
        return False

    def has_delete_permission(self, obj=None):
        if self.request.user.is_superuser or self.request.user.is_oper_mgr:
            return False
        return False

    def save_models(self):
        obj = self.new_obj
        request = self.request
        if obj.seller is None:
            obj.seller = request.user.seller
        super().save_models()

    def queryset(self):
        queryset = super().queryset()
        if self.request.user.seller:
            return queryset.filter(seller=self.request.user.seller)
        else:
            return queryset

    def seller_choices(self, field, request, params, model, model_admin, field_path):
        if self.request.user.station:
            seller_lst = Seller.objects.filter(id=self.request.user.station.seller.id).values("id", "name")
        elif self.request.user.seller:
            seller_lst = Seller.objects.filter(id=self.request.user.seller.id).values("id", "name")
        else:
            return field.get_choices(include_blank=False)
        print(seller_lst)
        # 返回格式 [('pk','标题'),]
        return list(((seller.get('id'), seller.get('name')) for seller in seller_lst))


xadmin.site.register(CardRecharge, CardRechargeAdmin)


class CardOrderAdmin(object):
    list_display = [
        'out_trade_no', 'name', 'charg_mode', 'charg_pile', 'gun_num', 'total_minutes', 'total_readings', 'begin_time', 'pay_time',
        'consum_money', 'cash_fee', 'status'
    ]
    search_fields = ['out_trade_no', 'charg_pile__pile_sn', 'name', 'openid']
    list_filter = ['charg_status', 'begin_time', 'status']
    exclude = ['charg_type']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    relfield_style = 'fk_ajax'
    aggregate_fields = {"total_readings": "sum", 'cash_fee': "sum"}

    form_layout = (
        Main(
            Fieldset(
                '订单信息',
                Row('out_trade_no', 'name'),
                Row('seller', 'station'),
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

    def queryset(self):
        queryset = super().queryset()

        if self.request.user.station:
            return queryset.filter(charg_pile__station=self.request.user.station, start_model=1)
        elif self.request.user.seller:
            return queryset.filter(charg_pile__station__seller=self.request.user.seller, start_model=1)
        else:
            return queryset.filter(start_model=1)

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


xadmin.site.register(CardOrder, CardOrderAdmin)