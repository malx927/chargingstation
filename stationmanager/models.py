# coding= utf8
from datetime import datetime
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db import models
from django.conf import settings
import time

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from codingmanager.models import PileType, FaultCode, PriceType, AreaCode
from codingmanager.constants import *


class Seller(models.Model):
    """
    运营商信息表
    """
    name = models.CharField(verbose_name='运营商名称', max_length=64)
    org_code = models.CharField(verbose_name='组织机构代码', max_length=9)
    bank_name = models.CharField(verbose_name='开户银行', max_length=100, blank=True, default='')
    account_name = models.CharField(verbose_name='银行账户名', max_length=36, blank=True, default='')
    account_number = models.CharField(verbose_name='银行账号', max_length=24, blank=True, default='')
    tax_number = models.CharField(verbose_name='税号', max_length=24, blank=True, default='')
    legal_person = models.CharField(verbose_name='法人代表', max_length=24, blank=True, default='')
    id_card = models.CharField(verbose_name='身份证号', max_length=20, blank=True, default='')
    address = models.CharField(verbose_name='联系地址', max_length=120, blank=True, default='')
    contact_man = models.CharField(verbose_name='联系人', max_length=64, blank=True, default='')
    telephone = models.CharField(verbose_name='联系电话', max_length=32)
    short_name = models.CharField(verbose_name='简称', max_length=32, blank=True, default='')
    parent = models.ForeignKey('self', verbose_name='上级运营商', blank=True, null=True, on_delete=models.SET_NULL)
    status = models.IntegerField(verbose_name='状态', choices=((0, '有效'), (1, '禁用')), default=0)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now=True)

    class Meta:
        verbose_name = '运营商管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Station(models.Model):
    """
    充电站管理
    """
    name = models.CharField(verbose_name='充电站名称', max_length=100)
    province = models.ForeignKey(AreaCode, verbose_name='省份', related_name='provinces', null=True, on_delete=models.SET_NULL, db_constraint=False)
    city = models.ForeignKey(AreaCode, verbose_name='城市', related_name='cities', null=True, on_delete=models.SET_NULL, db_constraint=False)
    district = models.ForeignKey(AreaCode, verbose_name='县区', related_name='districts', null=True, on_delete=models.SET_NULL, db_constraint=False)
    address = models.CharField(verbose_name='详细地址', max_length=50)
    longitude = models.DecimalField(verbose_name='经度', default=0, decimal_places=6, max_digits=12)
    latitude = models.DecimalField(verbose_name='纬度', default=0, decimal_places=6, max_digits=12)
    altitude = models.CharField(verbose_name='海拔高度', max_length=20, blank=True, null=True)
    seller = models.ForeignKey(Seller, verbose_name='所属运营商', null=True, on_delete=models.SET_NULL, db_constraint=False)
    equip_owner_id = models.CharField(verbose_name='设备所属方ID', max_length=9, help_text="组织机构代码")
    station_type = models.IntegerField(verbose_name="站点类型", choices=STATION_TYPES)
    station_status = models.IntegerField(verbose_name="站点状态", choices=STATION_STATUS)
    construction = models.IntegerField(verbose_name="建设场所", choices=STATION_PLACE)
    telephone = models.CharField(verbose_name='联系电话', max_length=24)
    telephone1 = models.CharField(verbose_name='联系电话1', max_length=24, blank=True, null=True)
    dicount = models.DecimalField(verbose_name='打折率', max_digits=4, decimal_places=1, default=0.0, blank=True, choices=DICOUNT_MODE)
    is_reduction = models.IntegerField(verbose_name='是否满减', default=0,  choices=((0, '否'), (1, '是')))
    purchase_amount = models.IntegerField(verbose_name='满减限额值(满)', blank=True, default=0, help_text='例如:满300减50')
    reduction = models.IntegerField(verbose_name='减免额度(减)', blank=True, default=0)
    # charg_policy = models.IntegerField(verbose_name='充电策略', default=0, blank=True, choices=CHARGING_PILE_POLICY)
    subscribe_fee = models.DecimalField(verbose_name='预约费', max_digits=6, decimal_places=2, default=0.0, blank=True)
    is_seat_fee = models.IntegerField(verbose_name="是否收占位费", default=0,  choices=((0, '否'), (1, '是')))
    free_min = models.IntegerField(verbose_name="免占位费时间", default=0)
    occupy_fee = models.DecimalField(verbose_name='每10分钟占位费', max_digits=6, decimal_places=2, default=0.0, blank=True)
    low_fee = models.DecimalField(verbose_name='小电流补偿费', max_digits=6, decimal_places=2, default=0.0, blank=True)
    low_restrict_val = models.IntegerField(verbose_name='小电流限制值',  default=0, blank=True)
    service_ratio = models.IntegerField(verbose_name='每订单服务费收取比例', blank=True, default=0, help_text='执行运营商收费时,公司收取')
    rebate_ratio = models.IntegerField(verbose_name='每订单返利提取比例', blank=True, default=0, help_text='执行公司收费时,给运营商返现')
    offline_sub_fee = models.DecimalField(verbose_name='离线预约费', max_digits=6, decimal_places=2, default=0.0, blank=True)
    offline_occupy_fee = models.DecimalField(verbose_name='离线占位费', max_digits=6, decimal_places=2, default=0.0, blank=True)
    offline_low_fee = models.DecimalField(verbose_name='离线小电流补偿费', max_digits=6, decimal_places=2, default=0.0, blank=True)
    offline_low_restrict = models.DecimalField(verbose_name='离线启用小电流限制', max_digits=6, decimal_places=2, default=0.0, blank=True)
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '充电站管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def province_city_district(self):
        province = self.province.name if self.province is not None else ''
        city = self.city.name if self.city is not None else ''
        district = self.district.name if self.district is not None else ''
        return '{}{}{}'.format(province, city, district)
    province_city_district.short_description = '省市县区'

    def get_detail_address(self):
        return "{}{}{}{}".format(self.province.name, self.city.name, self.district.name, self.address)

    def pile_totals(self):
        return self.chargingpile_set.all().count()

    def get_gun_totals(self):
        counts = ChargingGun.objects.filter(charg_pile__station=self).count()
        free_counts = ChargingGun.objects.filter(charg_pile__station=self, work_status=0).count()
        print(counts, free_counts)
        return '{}/{}'.format(free_counts, counts)

    def get_gun_totals_by_type(self):
        dc_counts = ChargingGun.objects.filter(charg_pile__station=self, charg_pile__pile_type_id__in=[1, 2]).count()  # 直流
        ac_counts = ChargingGun.objects.filter(charg_pile__station=self,  charg_pile__pile_type_id__in=[5, 6]).count()  # 交流
        data = {
            "dc_counts": dc_counts,
            "ac_counts": ac_counts,
        }
        return data

    def get_gun_totals_by_status(self):
        data = ChargingGun.objects.filter(charg_pile__station=self).values("work_status").annotate(counts=Count("id"))
        ret_data = {
            "free": 0,
            "charging": 0,
            "fault": 0,
            "offline": 0,
        }
        for d in data:
            if d["work_status"] == 0:
                ret_data["free"] = d["counts"]
            elif d["work_status"] == 1 or d["work_status"] == 3:
                ret_data["charging"] += d["counts"]
            elif d["work_status"] == 2:
                ret_data["fault"] = d["counts"]
            elif d["work_status"] == 9:
                ret_data["offline"] = d["counts"]
        return ret_data

    def get_station_price(self):
        staiton_price = self.chargingprice_set.filter(default_flag=1).first()
        return staiton_price

    def get_absolute_url(self):
        return reverse('station-detail', kwargs={'stationid': self.id})


class StationImage(models.Model):
    """电站图片"""
    station = models.ForeignKey(Station, verbose_name='所属充电站')
    image = models.ImageField(verbose_name='电站图片', upload_to='stations/', blank=True, null=True)
    create_at = models.DateTimeField(verbose_name="添加时间", auto_now_add=True)

    def __str__(self):
        return self.station.name

    class Meta:
        verbose_name = '充电站图片'
        verbose_name_plural = verbose_name


# 充电桩管理
class ChargingPile(models.Model):
    """
    充电桩信息
    """
    name = models.CharField(verbose_name='名称', max_length=64)
    pile_sn = models.CharField(verbose_name='电桩编码(SN)', max_length=32, unique=True)
    pile_type = models.ForeignKey(PileType, verbose_name='电桩类型', on_delete=models.SET_NULL, null=True, db_constraint=False)
    pile_mode = models.IntegerField(verbose_name='电桩模式', default=0, blank=True, choices=CHARGING_PILE_MODE)
    max_gun = models.IntegerField(verbose_name='最大枪口数', blank=True, default=0)
    fireware = models.CharField(verbose_name='固件版本', max_length=24, blank=True, null=True)
    business_mode = models.IntegerField(verbose_name='运营属性', blank=True, null=True, choices=BUSINESS_MODE)
    station = models.ForeignKey(Station, verbose_name='所属充电站', on_delete=models.SET_NULL, blank=True, null=True, db_constraint=False)
    power = models.DecimalField(verbose_name='充电设备总功率', max_digits=7, decimal_places=1, default=0)
    symbol_4g = models.NullBooleanField(verbose_name='4G使用标志', blank=True, null=True)
    symbol_eth = models.NullBooleanField(verbose_name='ETH使用标志', blank=True, null=True)
    restart_nums = models.IntegerField(verbose_name='4G重启次数', blank=True, default=0)
    gun_max_voltage = models.IntegerField(verbose_name='单枪最大输出电压', blank=True, null=True)
    gun_min_voltage = models.IntegerField(verbose_name='单枪最小输出电压', blank=True, null=True)
    gun_max_current = models.IntegerField(verbose_name='单枪最大输出电流', blank=True, null=True)
    gun_min_current = models.IntegerField(verbose_name='单枪最小输出电流', blank=True, null=True)
    charg_policy = models.IntegerField(verbose_name='充电策略', default=0, blank=True, choices=CHARGING_PILE_POLICY)
    low_restrict = models.IntegerField(verbose_name='输出小电流限制', default=0, choices=SMALL_CURRENT_STATUS)
    low_offset = models.IntegerField(verbose_name='输出小电流补偿', default=0, choices=SMALL_CURRENT_STATUS)
    subscribe_status = models.IntegerField(verbose_name='预约费收取', default=0, choices=SMALL_CURRENT_STATUS)
    occupy_status = models.IntegerField(verbose_name='充满占位费', default=0, choices=SMALL_CURRENT_STATUS)
    low_cur_value = models.IntegerField(verbose_name='限制输出小电流值', blank=True, default=0)
    low_offset_value = models.IntegerField(verbose_name='小电流补偿(每分钟)', blank=True, default=0)
    subscribe_fee = models.IntegerField(verbose_name='预约费(每5分钟)', blank=True, default=0)
    occupy_fee = models.IntegerField(verbose_name='占位费', blank=True, default=0)
    faults = models.ForeignKey(FaultCode, verbose_name='故障原因', on_delete=models.SET_NULL, blank=True, null=True, db_constraint=False)
    qrcode = models.ImageField(verbose_name='二维码', upload_to='qrcode/', blank=True, null=True)
    is_subsidy = models.IntegerField(verbose_name='运营补贴', default=0, choices=((0, '否'), (1, '运营补贴')))
    sub_status = models.IntegerField(verbose_name='订阅状态', default=0, choices=((0, '离线'), (1, '订阅')))
    sub_time = models.DateTimeField(verbose_name='出厂时间', blank=True, null=True)
    group = models.ForeignKey(Group, verbose_name='单位', blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='添加用户', blank=True, null=True, db_constraint=False)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '充电桩管理'
        verbose_name_plural = verbose_name

    def get_guns(self):
        return self.charginggun_set.all()

    def get_work_status(self):
        state = ''
        for gun in self.charginggun_set.all():
            work_status = gun.get_work_status_display()
            if work_status is None:
                work_status = '无'

            state += '<span>枪口{}:{}</span> '.format(gun.gun_num, work_status)
        return mark_safe(state)
    get_work_status.short_description = '运行状态'

    def get_order_url(self):
        return './chargingorder/order/?_rel_charg_pile__id__exact={}'.format(self.id)


class ChargingGun(models.Model):
    """
    充电桩枪信息表
    """
    gun_num = models.CharField(verbose_name='枪口号', max_length=12, choices=GUN_NUM)
    charg_pile = models.ForeignKey(ChargingPile, verbose_name='充电桩', on_delete=models.CASCADE)
    gun_type = models.IntegerField(verbose_name='枪口类型', choices=CONNECTOR_TYPE, default=4)
    work_status = models.IntegerField(verbose_name='工作状态', default=9, blank=True, choices=GUN_WORKING_STATUS)
    charg_status = models.ForeignKey(FaultCode, verbose_name='充电状态', null=True, blank=True)
    voltage_upper_limits = models.IntegerField(verbose_name='额定电压上限', default=0)
    voltage_lower_limits = models.IntegerField(verbose_name='额定电压下限', default=0)
    current = models.IntegerField(verbose_name='额定电流', default=0)
    power = models.IntegerField(verbose_name='额定功率', default=0)
    nationalstandard = models.IntegerField(verbose_name='国家标准', choices=NATIONAL_STANDARD, default=2)
    cc_status = models.IntegerField(verbose_name='CC状态', null=True, blank=True, choices=CC_STATUS)
    cp_status = models.IntegerField(verbose_name='CP状态', null=True, blank=True, choices=CP_STATUS)
    gun_temp_status = models.IntegerField(verbose_name='枪头温度状态', null=True, blank=True, choices=GUN_TEMPERATURE)
    elec_lock_status = models.IntegerField(verbose_name='电子锁状态', null=True, blank=True, choices=ELEC_LOCK_STATUS)
    relay_status = models.IntegerField(verbose_name='继电器状态', null=True, blank=True, choices=RELAY_STATUS)
    fuse_status = models.IntegerField(verbose_name='融断器状态', null=True, blank=True, choices=FUSE_STATUS)
    gun_temp = models.IntegerField(verbose_name='枪温度PT-1', null=True, blank=True)
    cab_temp = models.IntegerField(verbose_name='柜内温度', null=True, blank=True)
    subscribe_min = models.IntegerField(verbose_name='预约分钟数', null=True, blank=True)
    recharge_min = models.IntegerField(verbose_name='充电分钟数', null=True, blank=True)
    occupy_min = models.IntegerField(verbose_name='占位分钟数', null=True, blank=True)
    qrcode = models.ImageField(verbose_name='二维码', upload_to='qrcode/', blank=True, null=True) # pile_sn + gun_num
    add_time = models.DateTimeField(verbose_name='时间', auto_now=True)
    out_trade_no = models.CharField(verbose_name="最新订单号", max_length=32, blank=True, null=True)
    order_time = models.DateTimeField(verbose_name='订单时间', blank=True, null=True)

    def __str__(self):
        return '{0}-{1}'.format(self.charg_pile.pile_sn, self.gun_num)

    class Meta:
        verbose_name = '充电桩枪口信息'
        verbose_name_plural = verbose_name

    def charging_pile_sn(self):
        return self.charg_pile.pile_sn

    charging_pile_sn.short_description = '充电桩SN'


class ChargingPileStatus(models.Model):
    pile = models.ForeignKey(ChargingPile, verbose_name="充电桩")
    cabinet_temp1_status = models.IntegerField(verbose_name='柜内温度PT-1状态', default=0, choices=CABINET_TEMPERATURE_STATUS)
    cabinet_temp2_status = models.IntegerField(verbose_name='柜内温度PT-2状态', default=0, choices=CABINET_TEMPERATURE_STATUS)
    cabinet_temp1 = models.DecimalField(verbose_name='柜内温度PT-1', blank=True, null=True, max_digits=5, decimal_places=2)
    cabinet_temp2 = models.DecimalField(verbose_name='柜内温度PT-2', blank=True, null=True, max_digits=5, decimal_places=2)
    spd_status = models.IntegerField(verbose_name='防雷器状态', default=0, choices=SPD_EMERGENCY_STATUS)
    emerg_stop_status = models.IntegerField(verbose_name='防雷器状态', default=0, choices=SPD_EMERGENCY_STATUS)
    water_status = models.IntegerField(verbose_name='水浸状态', default=0, blank=True, choices=WATER_INPUT_STATUS)
    door_status = models.IntegerField(verbose_name='开门状态', default=0, blank=True, choices=DOOR_STATUS)
    power_fail_status = models.IntegerField(verbose_name='掉电状态', default=0, blank=True, choices=POWER_FAIL_STATUS)
    elec_leak_status = models.IntegerField(verbose_name='漏电状态', default=0, blank=True, choices=ELEC_LEAK_STATUS)

    def __str__(self):
        return self.pile.pile_sn

    class Meta:
        verbose_name = '充电桩状态信息'
        verbose_name_plural = verbose_name


class FaultChargingGun(models.Model):
    """
    故障充电桩枪信息表
    """
    gun_num = models.CharField(verbose_name='枪口号', max_length=12, choices=GUN_NUM)
    charg_pile = models.ForeignKey(ChargingPile, verbose_name='充电桩', on_delete=models.CASCADE)
    work_status = models.IntegerField(verbose_name='工作状态', default=9, blank=True, choices=GUN_WORKING_STATUS)
    charg_status = models.ForeignKey(FaultCode, verbose_name='充电状态', null=True, blank=True)
    fault_time = models.DateTimeField(verbose_name="故障时间", blank=True, null=True)
    repair_time = models.DateTimeField(verbose_name="修复时间", blank=True, null=True)
    repair_persons = models.CharField(verbose_name="修复人", blank=True, null=True, max_length=64)
    repair_flag = models.BooleanField(verbose_name="修复标志", default=False)

    class Meta:
        verbose_name = '故障枪口信息'
        verbose_name_plural = verbose_name


# 充电价格表
class ChargingPrice(models.Model):
    """
    价格策略管理（主表）
    """
    FLAGS = (
        (0, '--无--'),
        (1, '默认价格策略'),
    )
    station = models.ForeignKey(Station, verbose_name='充电站', null=True, on_delete=models.SET_NULL)
    type = models.IntegerField(verbose_name='收费类型', choices=CHARGING_PRICE_TYPE)
    parking_fee = models.DecimalField(verbose_name='停车费(元/小时)', max_digits=5, decimal_places=2, default=0)
    default_flag = models.IntegerField(verbose_name='默认价格策略', default=0, choices=FLAGS, help_text='每个电站设置一个默认策略')

    def __str__(self):
        return self.get_type_display()

    class Meta:
        verbose_name = '价格策略管理'
        verbose_name_plural = verbose_name

    def get_current_serice_price(self):
        cur_time = datetime.now().time()
        price_detail = self.prices.filter(begin_time__lte=cur_time, end_time__gte=cur_time).first()
        if price_detail:
            return price_detail.service_price
        else:
            return 0


class ChargingPriceDetail(models.Model):
    """
    收费价格表（明细表）
    """
    charg_price = models.ForeignKey(ChargingPrice, verbose_name='价格类型', related_name="prices")
    begin_time = models.TimeField(verbose_name='开始时间')
    end_time = models.TimeField(verbose_name='截止时间')
    price = models.DecimalField(verbose_name='电价(元/度)', max_digits=6, decimal_places=2, default=0, blank=True)
    service_price = models.DecimalField(verbose_name='服务费(元/度)', max_digits=6, decimal_places=2, default=0, blank=True)

    def __str__(self):
        return '{0}-{1}'.format(self.begin_time.strftime("%H:%M"), self.end_time.strftime("%H:%M"))

    class Meta:
        verbose_name = '价格明细表'
        verbose_name_plural = verbose_name
        ordering = ["begin_time"]


class PowerModuleStatus(models.Model):
    """
    电源模块状态
    """
    name = models.IntegerField(verbose_name='模块序号')
    pile = models.ForeignKey(ChargingPile, verbose_name='电桩名称',  on_delete=models.CASCADE)
    pile_sn = models.CharField(verbose_name='电桩编号', max_length=32, blank=True, null=True)
    status = models.IntegerField(verbose_name='状态', blank=True, null=True, choices=POWER_MODULE_STATUS)
    update_time = models.DateTimeField(verbose_name='更新时间',default=datetime.now)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '电源模块'
        verbose_name_plural = verbose_name