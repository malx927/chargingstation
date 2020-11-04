# coding=utf8
import os
import time

from django.db.models import Q
from django.forms import CharField
import qrcode
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

from codingmanager.models import AreaCode
from users.models import UserProfile
from xadmin.sites import site
from stationmanager.plugins import DashBoardPlugin, WarningPlugin
import xadmin
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper, AppendedText, Col, TabHolder, Tab
from stationmanager.utils import create_qrcode
from xadmin import views
from xadmin.plugins.inline import Inline
from xadmin.views import Dashboard, CommAdminView
from xadmin.views.website import LoginView
from .models import Seller, Station, ChargingPile, ChargingPrice, ChargingPriceDetail, ChargingGun, \
    PowerModuleStatus, StationImage, FaultChargingGun

site.register_plugin(DashBoardPlugin, Dashboard)
site.register_plugin(WarningPlugin, CommAdminView)


# 修改登录界面标题
class LoginViewAdmin(LoginView):
    title = settings.SITE_TITLE


xadmin.site.register(LoginView, LoginViewAdmin)


class BaseXadminSetting(object):
    enable_themes = True
    use_bootswatch = True


xadmin.site.register(views.BaseAdminView, BaseXadminSetting)


class CommXadminSetting(object):
    site_title = settings.SITE_TITLE
    # img_url = "/static/stationmanager/images/logo-1.png"
    # site_title = mark_safe("<img src='{}' width='120' height='50'/>{}".format(img_url, settings.SITE_TITLE))
    site_footer = settings.SITE_FOOTER


xadmin.site.register(views.CommAdminView, CommXadminSetting)


class SellerAdmin(object):
    """
    运营商信息
    """
    list_display = ['id', 'name', 'telephone', 'address', 'org_code', 'parent']
    search_fields = ['name', 'telephone', 'address', 'org_code']
    list_display_links = ('name',)
    model_icon = 'fa fa-sitemap'
    list_export = ('xls', 'xml', 'json')
    save_on_top = False
    form_layout = (
        Fieldset(
            '基础信息',
            Row('name', 'org_code'),
            Row('address', 'short_name'),
            Row('contact_man', 'telephone'),
            Row('legal_person', 'id_card'),
        ),
        Fieldset(
            '公司银行信息',
            Row('bank_name', 'account_name'),
            Row('account_number', 'tax_number'),
        ),
        Fieldset(
            '其他信息',
            Row('parent', 'status'),
        )

    )

    def queryset(self):
        queryset = super(SellerAdmin, self).queryset()
        if self.request.user.seller:
            return queryset.filter(id=self.request.user.seller.id)
        elif self.request.user.station:
            return Seller.objects.none()
        return queryset

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'parent':
            if not self.request.user.is_superuser:
                kwargs['queryset'] = Seller.objects.filter(id=self.request.user.seller.id)
        return super(SellerAdmin, self).formfield_for_dbfield(db_field,  **kwargs)


xadmin.site.register(Seller, SellerAdmin)


class ChargingPriceInline(object):
    """
    枪口信息
    """
    model = ChargingPrice
    extra = 1
    style = "accordion"


class StationImageInline(object):
    """电站图片"""
    model = StationImage
    extra = 1
    style = "accordion"


class StationAdmin(object):
    list_display = ['id', 'name', 'seller', 'province_city_district', 'address',  'telephone',  'station_status', 'station_type']
    list_display_links = ('name',)
    search_fields = ['name',  'address', 'seller.name', 'telephone', 'telephone1']
    list_filter = ['seller', 'dicount']
    model_icon = 'fa fa-sitemap'
    relfield_style = 'fk_ajax'
    inlines = [StationImageInline]

    form_layout = (
        Main(
            Fieldset(
                '基本信息',
                Row('name', 'seller'),
                Row('province', 'city'),
                Row('district', 'address'),
                Row('equip_owner_id', 'station_status'),
                Row('station_type', 'construction'),
                Row('telephone', 'telephone1'),
                Row('is_show', None),
            ),
            Fieldset(
                '费用收取设置',
                Row(
                    'is_seat_fee',
                    AppendedText('occupy_fee', '元'),
                ),
                Row(
                    AppendedText('free_min', '分钟'),
                    AppendedText('subscribe_fee', '元'),
                ),
                Row(
                    AppendedText('low_restrict_val', '毫安'),
                    AppendedText('low_fee', '元')
                ),
                Row(
                    AppendedText('service_ratio', '%'),
                    AppendedText('rebate_ratio', '%')
                ),
            ),
            Fieldset(
                '离线情况设置',
                Row(
                    AppendedText('offline_sub_fee', '元'),
                    AppendedText('offline_occupy_fee', '元'),
                ),
                Row(
                    AppendedText('offline_low_fee', '元'),
                    'offline_low_restrict',
                )
            ),
        ),
        Side(
            Fieldset(
                '优惠方案',
                'dicount',
                'is_reduction',
                AppendedText('purchase_amount', '元'),
                AppendedText('reduction', '元')
            ),
            Fieldset(
                '地理信息',
                'latitude', 'longitude', 'altitude',
            ),
        ),

    )

    def get_media(self):
        media = super(StationAdmin, self).get_media()
        path = self.request.get_full_path()
        if "add" in path or 'update' in path:
            media.add_js([self.static('stationmanager/js/xadmin.areacode.js')])
        return media

    def queryset(self):
        queryset = super(StationAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(id=self.request.user.station.id)
        elif self.request.user.seller:
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

        return list(((seller.get('id'), seller.get('name')) for seller in seller_lst))

    def formfield_for_dbfield(self, db_field,  **kwargs):
        # print(self.new_obj)
        if db_field.name == 'seller':
            if not self.request.user.is_superuser:
                kwargs['queryset'] = Seller.objects.filter(id=self.request.user.seller.id)

        if db_field.name == 'province':
            kwargs['queryset'] = AreaCode.objects.extra(where=['length(code)=2'])

        if db_field.name == 'city':
            kwargs['queryset'] = AreaCode.objects.extra(where=['length(code)=4'])

        if db_field.name == 'district':
            kwargs['queryset'] = AreaCode.objects.extra(where=['length(code)=6'])

        # if db_field.name == 'fee_scale':
        #     kwargs['queryset'] = AreaCode.objects.extra(where=['length(code)=6'])

        return super(StationAdmin, self).formfield_for_dbfield(db_field,  **kwargs)


xadmin.site.register(Station, StationAdmin)


class ChargingGunInline(object):
    """
    枪口信息
    """
    model = ChargingGun
    extra = 1
    # exclude = ['out_trade_no']
    style = "accordion"
    # readonly_fields = ['qrcode']
    form_layout = (
        Fieldset(
            '枪口信息',
            Row('gun_num', 'charg_status'),
            Row('gun_type', 'nationalstandard'),
            Row(
                AppendedText('voltage_upper_limits', 'V'),
                AppendedText('voltage_lower_limits', 'V'),
            ),
            Row(
                AppendedText('current', 'A'),
                AppendedText('power', 'KW'),
            ),
            Row('work_status', None),
            Row('cc_status', 'cp_status'),
            Row('gun_temp_status', 'elec_lock_status'),
            Row('relay_status', 'fuse_status'),
            Row('gun_temp', 'cab_temp'),
        ),
        Fieldset(
            '其他信息',
            Row('occupy_min', 'recharge_min'),
            Row('subscribe_min', 'qrcode'),
        ),

    )


class ChargingPileAdmin(object):
    """
    充电桩管理
    """
    list_display = ['name', 'pile_sn', 'pile_type', 'station', 'pile_mode', 'business_mode',
                    'get_work_status']
    list_display_links = ('name',)
    search_fields = ['pile_sn', 'name', 'pile_type', 'station']
    exclude = ["qrcode", 'group']
    list_filter = ['pile_type', 'station', 'pile_mode', 'business_mode']
    readonly_fields = ['user']

    model_icon = 'fa fa-sitemap'
    show_all_rel_details = False
    # list_editable = ['pile_type', 'pile_sn']
    refresh_times = [3, 5]  # 计时刷新
    save_as = True
    style_fields = {
        "low_restrict": "radio-inline", "low_offset": "radio-inline",
        "subscribe_status": "radio-inline",
        "occupy_status": "radio-inline",
        'sub_status': "radio-inline",
    }

    form_layout = (
        Main(
            TabHolder(
                Tab(
                    '基础信息设置',
                    Fieldset(
                        '基础信息',
                        Row('name', 'pile_type'),
                        Row('pile_sn', 'power'),
                        Row('station', 'pile_mode'),
                        Row('business_mode', 'fireware'),
                        Row('symbol_4g', 'symbol_eth'),
                        Row('sub_time'),
                        Row('is_subsidy', 'faults'),
                    ),
                    Inline(ChargingGun),
                    css_id="base_info",
                ),
                Tab(
                    '其他设置',
                    Fieldset(
                        "预约及占位设置",
                        'charg_policy',
                        Row('subscribe_status', AppendedText('subscribe_fee', '元')),
                        Row('occupy_status', AppendedText('occupy_fee', '元')),
                    ),
                    Fieldset(
                        "小电流设置参数",
                        Row('low_restrict', AppendedText('low_cur_value', '毫安')),
                        Row('low_offset', AppendedText('low_offset_value', '元')),
                    ),
                    Fieldset(
                        "单枪参数",
                        Row(AppendedText('gun_max_voltage', '伏'), AppendedText('gun_min_voltage', '伏')),
                        Row(AppendedText('gun_max_current', '安'), AppendedText('gun_min_current', '安')),
                    ),
                    css_id="other_set",
                ),
            ),
        ),
        Side(
            Fieldset("其他信息", 'sub_status',  'user', 'max_gun', 'restart_nums'),
        )
    )

    inlines = [ChargingGunInline]

    def queryset(self):
        queryset = super(ChargingPileAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(station__seller=self.request.user.seller)
        else:
            return queryset

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'station':
            if not self.request.user.is_superuser:
                kwargs['queryset'] = Station.objects.filter(seller=self.request.user.seller)
        return super(ChargingPileAdmin, self).formfield_for_dbfield(db_field,  **kwargs)

    def save_models(self):
        obj = self.new_obj
        request = self.request
        obj.user = request.user
        obj.group = request.user.groups.first()

        super(ChargingPileAdmin, self).save_models()

    def save_related(self):
        obj = self.new_obj
        super(ChargingPileAdmin, self).save_related()
        for inst in obj.charginggun_set.all():
            self.save_image(inst)

    def save_image(self, instance):
        upload_path = instance.qrcode.field.upload_to
        dirs = os.path.join(settings.MEDIA_ROOT, upload_path)
        if not os.path.exists(dirs):
            os.makedirs(dirs)

        domain_url = settings.ROOT_URL if settings.ROOT_URL else "http://" + self.request.get_host()
        # domain_url = "http://" + self.request.get_host()
        path = reverse('order-prepay', kwargs={'pile_sn': instance.charg_pile.pile_sn, "gun_num": instance.gun_num})
        qrcode_content = '{0}{1}'.format(domain_url, path)
        image = create_qrcode(qrcode_content)
        image_url = '{0}_{1}.png'.format(instance.charg_pile.pile_sn, instance.gun_num)
        image.save(os.path.join(dirs, image_url), quality=100)
        instance.qrcode = '{0}{1}'.format(upload_path, image_url)
        instance.save()

    def station_choices(self, field, request, params, model, model_admin, field_path):
        if self.request.user.station:
            stations = Station.objects.filter(id=self.request.user.station.id).values("id", "name")
        elif self.request.user.seller:
            stations = Station.objects.filter(seller_id=self.request.user.seller.id).values("id", "name")
        else:
            return field.get_choices(include_blank=False)

        return list(((station.get('id'), station.get('name')) for station in stations))


xadmin.site.register(ChargingPile, ChargingPileAdmin)


class ChargingGunAdmin(object):
    list_display = ['charg_pile', 'charging_pile_sn', 'gun_num', 'work_status', 'charg_status', 'cc_status', 'cp_status', 'gun_temp_status', 'elec_lock_status', 'relay_status',]
    search_fields = ['gun_num', 'charg_pile__pile_sn']
    list_display_links = ['gun_num', 'charg_pile']
    list_filter = ['charg_pile', 'work_status']
    model_icon = 'fa fa-sitemap'
    show_all_rel_details = False
    # save_as = True
    # save_on_top = True

    form_layout = (
        Fieldset(
            '枪口信息',
            Row('gun_num', 'charg_pile'),
            Row('gun_type', 'nationalstandard'),
            Row(
                AppendedText('voltage_upper_limits', 'V'),
                AppendedText('voltage_lower_limits', 'V'),
            ),
            Row(
                AppendedText('current', 'A'),
                AppendedText('power', 'KW'),
            ),
            Row('work_status', 'charg_status'),
            Row('cc_status', 'cp_status'),
            Row('gun_temp_status', 'elec_lock_status'),
            Row('relay_status', 'fuse_status'),
            Row('gun_temp', 'cab_temp'),
        ),
        Fieldset(
            '其他信息',
            Row('occupy_min', 'subscribe_min',),
            Row('recharge_min', "qrcode"),

        ),
        Fieldset(
            '最近订单',
            Row('out_trade_no', 'order_time', ),
        ),
    )

    def queryset(self):
        queryset = super(ChargingGunAdmin, self).queryset()
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

        return super(ChargingGunAdmin, self).formfield_for_dbfield(db_field,  **kwargs)

    def save_models(self):
        obj = self.new_obj
        request = self.request

        upload_path = obj.qrcode.field.upload_to
        dirs = os.path.join(settings.MEDIA_ROOT, upload_path)

        if not os.path.exists(dirs):
            os.makedirs(dirs)

        domain_url = settings.ROOT_URL if settings.ROOT_URL else "http://" + request.get_host()
        # domain_url ="http://" + request.get_host()
        path = reverse('order-prepay', kwargs={'pile_sn': obj.charg_pile.pile_sn, "gun_num": obj.gun_num})
        qrcode_content = '{0}{1}'.format(domain_url, path)
        image = create_qrcode(qrcode_content)
        image_url = '{0}_{1}.png'.format(obj.charg_pile.pile_sn, obj.gun_num)
        image.save(os.path.join(dirs, image_url), quality=100)
        obj.qrcode = '{0}{1}'.format(upload_path, image_url)
        return super(ChargingGunAdmin, self).save_models()

    def charg_pile_choices(self, field, request, params, model, model_admin, field_path):
        if self.request.user.station:
            piles = ChargingPile.objects.filter(station_id=self.request.user.station.id).values("id", "name")
        elif self.request.user.seller:
            piles = ChargingPile.objects.filter(station__seller_id=self.request.user.seller.id).values("id", "name")
        else:
            return field.get_choices(include_blank=False)
        return list(((pile.get('id'), pile.get('name')) for pile in piles))


xadmin.site.register(ChargingGun, ChargingGunAdmin)


class FaultChargingGunAdmin(object):
    list_display = ['charg_pile', 'gun_num', 'work_status', 'charg_status', 'fault_time', 'repair_time', 'repair_flag']
    search_fields = ['gun_num', 'charg_pile__pile_sn']
    list_display_links = ['gun_num', 'charg_pile']
    list_filter = ['charg_pile', 'work_status', 'charg_status']
    model_icon = 'fa fa-sitemap'
    show_all_rel_details = False

    def queryset(self):
        queryset = super(FaultChargingGunAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(charg_pile__station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(charg_pile__station__seller=self.request.user.seller)
        else:
            return queryset

    form_layout = (
        Fieldset('',
            Row('charg_pile', 'gun_num'),
            Row('work_status', 'charg_status'),
            Row('fault_time', 'repair_time'),
            Row('repair_persons'),
            Row('repair_flag'),
        ),
    )


xadmin.site.register(FaultChargingGun, FaultChargingGunAdmin)


class ChargingPriceDetailInline(object):
    """
    充电价格明细
    """
    model = ChargingPriceDetail
    extra = 3
    style = 'table'
    max_num = 8


class ChargingPriceAdmin(object):
    """
    充电价格表
    """
    list_display = ['station', 'type', 'parking_fee', 'default_flag']
    model_icon = 'fa fa-sitemap'
    save_as = True

    form_layout = (
        Fieldset(
            '基础信息',
            Row('station', 'type'),
            Row('parking_fee', 'default_flag'),
        ),
    )

    inlines = [ChargingPriceDetailInline]

    def queryset(self):
        queryset = super(ChargingPriceAdmin, self).queryset()
        if self.request.user.station:
            return queryset.filter(station=self.request.user.station)
        elif self.request.user.seller:
            return queryset.filter(station__seller=self.request.user.seller)
        else:
            return queryset

    def formfield_for_dbfield(self, db_field,  **kwargs):
        if db_field.name == 'station':
            if self.request.user.station:
                kwargs['queryset'] = Station.objects.filter(id=self.request.user.station.id)
            elif self.request.user.seller:
                kwargs['queryset'] = Station.objects.filter(seller=self.request.user.seller)

        return super(ChargingPriceAdmin, self).formfield_for_dbfield(db_field,  **kwargs)


xadmin.site.register(ChargingPrice, ChargingPriceAdmin)


class PowerModuleStatusAdmin(object):
    """
    电源模块状态
    """
    list_display = ['pile', 'pile_sn', 'name', 'status', 'update_time']
    search_fields = ['pile_sn', 'pile__name', 'pile__pile_sn', 'status', 'name']
    list_filter = ['pile', 'status', 'update_time']
    relfield_style = 'fk-ajax'
    model_icon = 'fa fa-sitemap'


xadmin.site.register(PowerModuleStatus, PowerModuleStatusAdmin)






