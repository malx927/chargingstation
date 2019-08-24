# coding=utf-8
import time
from datetime import datetime
import json
import random
import decimal

from codingmanager.constants import USER_CHARGING_MODE
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

# Create your views here.
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView

from stationmanager.models import ChargingPile, ChargingGun
from chargingorder.models import Order, OrderRecord
import paho.mqtt.publish as publish
from chargingstation import settings
from chargingorder.mqtt import server_send_charging_cmd, server_send_stop_charging_cmd
from wxchat.decorators import weixin_decorator
from wxchat.models import UserInfo, SubAccount
from wxchat.views import send_charging_start_message_to_user


@weixin_decorator
def index(request):
    piles = ChargingPile.objects.all()
    return render(request, template_name='chargingorder/charg_pile_list.html', context={"piles": piles})


def get_account_balance(openid, value=None):
    """账号余额"""
    try:
        user = UserInfo.objects.get(openid=openid)
        sub_account = user.is_sub_user()
        if sub_account:     # 附属账号
            account_balance = settings.MAIN_ACCOUNT_BALANCE
            if sub_account.main_user.account_balance() > account_balance:
                return True
        if value is None:
            account_balance = settings.ACCOUNT_BALANCE
        else:
            account_balance = value if value > settings.ACCOUNT_BALANCE else settings.ACCOUNT_BALANCE
        if user.account_balance() > account_balance:
            return True
    except UserInfo.DoesNotExist as ex:
        pass
    return False


class RechargeView(View):
    @method_decorator(weixin_decorator)
    def get(self, request, *args, **kwargs):
        """
        0、判断充电桩对应枪口当前状态，如果处于充电桩状态，则提示禁止充电操作
        1、判断最后一次提交时间，如果最后一次停车操作与当前时间差小于5分钟，禁止充电
        2、确定是否频繁做充电和停充操作，
        3、发出退款请求后要冻结账号，不允许充电，退款后解除冻结后可充电
        """
        openid = request.session.get("openid", None)
        try:
            user_info = UserInfo.objects.get(openid=openid)
        except UserInfo.DoesNotExist as ex:
            request.session.flush()
            return HttpResponseRedirect(request.get_full_path())
        b_created = request.session.get("created", None)
        if b_created:
            # 跳转到信息注册
            redirect_url = "{0}?url={1}".format(reverse("wxchat-register"), request.get_full_path())
            return HttpResponseRedirect(redirect_url)

        name = request.session.get("name", None)
        # 检查账号余额
        if openid is None:
            context = {
                "errmsg": "请先关注亚电新能源公众号"
            }
            return render(request, template_name="chargingorder/charging_pile_status.html", context=context)
        if not get_account_balance(openid):
            redirect_url = "{0}?url={1}".format(reverse('wxchat-order-pay'), request.get_full_path())
            print(redirect_url)
            return HttpResponseRedirect(redirect_url)

        pile_sn = kwargs.get('pile_sn', None)
        gun_num = kwargs.get('gun_num', None)
        try:
            pile_gun = ChargingGun.objects.get(charg_pile__pile_sn=pile_sn, gun_num=gun_num)
            if pile_gun.work_status == 0 or pile_gun.work_status is None:       # 空闲状态
                context = {
                    "pile_sn": pile_gun.charg_pile.pile_sn,
                    "gun_num": pile_gun.gun_num,
                }
                return render(request, template_name='chargingorder/recharge.html', context=context)  # 进入充电界面
            elif pile_gun.work_status in [1, 3]:         # 1-充电中 3-充电结束(未拔枪)
                order = Order.objects.filter(openid=openid, out_trade_no=pile_gun.out_trade_no, status__lte=2).first()
                print(openid, order)
                if order:
                    return render(request, template_name='weixin/recharge_order_status.html', context={"order": order})

        except ChargingGun.DoesNotExist as ex:
            print(ex)
            pile_gun = None

        return render(request, template_name="chargingorder/charging_pile_status.html", context={"pile_gun": pile_gun})

    def post(self, request, *args, **kwargs):
        """
        充电过程1、生成充电订单 2、调取微信支付功能，进行微信支付，成功后，服务端发送充值命令给充电桩
        """
        openid = request.session.get("openid", None)
        total_fee = request.POST.get("total_fee", "0")

        if not get_account_balance(openid, int(total_fee)):
            data = {
                "return_code": "success",
                "redirect_url": "{0}?url={1}".format(reverse('wxchat-order-pay'), request.get_full_path())
            }
            return JsonResponse(data)

        gun = self.get_charging_gun(request)
        if gun is None:
            data = {
                "return_code": "fail",
                "errmsg": "充电设备不存在",
            }
            return JsonResponse(data)
        cur_time = datetime.now()
        if gun.order_time and (cur_time - gun.order_time).seconds < 10:
            return render(request, template_name="chargingorder/charging_pile_status.html", context={"pile_gun": gun})

        charg_mode = request.POST.get('charg_mode', "0")  # 用户选择的充电方式

        if int(charg_mode) == 0:  # 充满为止
            order = self.full_recharge(request, *args, **kwargs)
        elif int(charg_mode) == 1:  # 按金额充电
            if total_fee is None or total_fee == '' or total_fee == '0':
                data = {
                    "return_code": "fail",
                    "errmsg": "请输入充电金额",
                }
                return JsonResponse(data)
            order = self.money_recharge(request, *args, **kwargs)
        elif int(charg_mode) == 2:  # 按时间充电
            order = self.min_recharge(request, *args, **kwargs)
        elif int(charg_mode) == 3:  # 按soc充电
            order = self.soc_recharge(request, *args, **kwargs)

        charg_pile = gun.charg_pile

        out_trade_no = order.out_trade_no
        data = {
            'pile_sn': charg_pile.pile_sn,
            'gun_num': order.gun_num,
            'out_trade_no': out_trade_no,
            'openid': order.openid,
            'charging_type': 0,  # 充电类型 1预约，0即时
            'subscribe_min': 0,
        }

        charg_policy = charg_pile.charg_policy  # 充电策略是否使用(D0：1使用充电策略，0系统默认策略)(电站还是电桩为准)
        data["use_policy_flag"] = charg_policy
        # 1使用充电策略
        if charg_policy == 1:
            data["continue_charg_status"] = 0  # 断网可继续充电  1断网可继续充电，0不可以(那些用户？)
            data["occupy_status"] = charg_pile.occupy_status  # 收取占位费 1收取占位费，0不收取
            data["subscribe_status"] = charg_pile.subscribe_status  # 收取预约费
            data["low_fee_status"] = charg_pile.low_offset  # 收取小电流补偿费
            data["low_restrict_status"] = charg_pile.low_restrict  # 限制小电流输出

        charging_policy_value = 0
        if charg_mode == 1:
            charging_policy_value = int(total_fee)
        elif charg_mode == 2:
            charging_policy_value = int(request.POST.get("charg_min_val", "0"))
        elif charg_mode == 3:
            charging_policy_value = int(request.POST.get("charg_soc_val", "0"))

        data["charging_policy_value"] = charging_policy_value

        server_send_charging_cmd(**data)
        send_charging_start_message_to_user(order)  # 发送模板消息，通知客户充电开始
        data = {
            "return_code": "success",
            "redirect_url": "{0}?out_trade_no={1}".format(reverse("order-recharge-status"), out_trade_no)
        }
        return JsonResponse(data)

    def get_request_params(self, request, *args, **kwargs):
        gun_num = request.POST.get('gun_num', '0')  # 枪口号
        openid = request.session.get("openid", None)  # 用户id(微信公众号openid)
        name = request.session.get("name", None)
        charg_mode = request.POST.get('charg_mode', "0")
        if name is None or len(name) == 0:
            name = request.session.get("nickname", '')  # 用户名称

        out_trade_no = '{0}{1}{2}{3}'.format('C', gun_num, datetime.now().strftime('%Y%m%d%H%M%S'),
                                             random.randint(10000, 100000))

        gun = self.get_charging_gun(request)
        params = {
            "gun_num": int(gun_num),
            "openid": openid,
            "name": name,
            "charg_mode": charg_mode,
            "charg_type": 0,            # 0后台 01本地离线
            "out_trade_no": out_trade_no,
            "charg_pile": gun.charg_pile,
            "gun": gun,
        }
        sub_account = SubAccount.objects.filter(sub_user__openid=openid).first()
        if sub_account:
            main_openid = sub_account.main_user.openid
            params["main_openid"] = main_openid
        return params

    def create_order(self, **kwargs):
        """创建订单"""
        gun = kwargs.pop("gun")
        order = Order.objects.create(**kwargs)
        gun.out_trade_no = order.out_trade_no
        gun.order_time = datetime.now()
        gun.save(update_fields={"out_trade_no", "order_time"})

        openid = kwargs.get("openid", None)
        # 添加到用户信息里
        UserInfo.objects.filter(openid=openid).update(out_trade_no=order.out_trade_no, last_charg_time=order.create_time)
        return order

    def get_charging_gun(self, request):
        """获得充电桩枪口信息"""
        try:
            pile_sn = request.POST.get('pile_sn', None)  # 充电桩Sn
            gun_num = request.POST.get('gun_num', '0')  # 枪口号
            pile_gun = ChargingGun.objects.get(gun_num=gun_num, charg_pile__pile_sn=pile_sn)
        except ChargingGun.DoesNotExist as ex:
            pile_gun = None
        return pile_gun

    def full_recharge(self, request, *args, **kwargs):
        params = self.get_request_params(request, *args, **kwargs)
        print("full_recharge:", params)
        order = self.create_order(**params)
        return order

    def money_recharge(self, request, *args, **kwargs):
        total_fee = request.POST.get("total_fee", '0')
        params = self.get_request_params(request, *args, **kwargs)
        params["total_fee"] = int(total_fee)
        order = self.create_order(**params)
        return order

    def min_recharge(self, request, *args, **kwargs):
        charg_min_val = request.POST.get("charg_min_val", 0)
        params = self.get_request_params(request, *args, **kwargs)
        params["charg_min_val"] = charg_min_val
        order = self.create_order(**params)
        return order

    def soc_recharge(self, request, *args, **kwargs):
        charg_soc_val = request.POST.get("charg_soc_val", 0)
        params = self.get_request_params(request, *args, **kwargs)
        params["charg_soc_val"] = charg_soc_val
        order = self.create_order(**params)
        return order


class StopChargeView(View):
    def get(self, request, *args, **kwargs):
        pile_sn = request.GET.get('pile_sn', None)
        gun_num = request.GET.get('gun_num', None)

    def post(self, request, *args, **kwargs):
        pass


class RechargeOrderStatusView(View):
    """充电订单状态"""
    def get(self, request, *args, **kwargs):
        try:
            out_trade_no = request.GET.get("out_trade_no", None)
            order = Order.objects.get(out_trade_no=out_trade_no)
        except Order.DoesNotExist as ex:
            order = None
        print("000000000000000")
        return render(request, template_name="weixin/recharge_order_status.html", context={"order": order})


class ChargingStatusView(View):
    """
    充电状态
    """
    def get(self, request, *args, **kwargs):
        pile_sn = request.GET.get('pile_sn', None)
        gun_num = request.GET.get('gun_num', None)
        context = {
            "pile_sn": pile_sn,
            "gun_num": gun_num,
        }
        return render(request, template_name="chargingorder/charging_pile_status.html", context=context)


class ChargingStatusDetailView(View):
    """
    充电状态
    """
    def get(self, request, *args, **kwargs):
        pile_sn = request.GET.get('pile_sn', None)
        gun_num = request.GET.get('gun_num', None)
        print(pile_sn, gun_num)
        orderRecord = OrderRecord.objects.filter(pile_sn=pile_sn, gun_num=gun_num).order_by("-update_time").first()
        data = {
            "success": "false",
        }
        if orderRecord:
            data["success"] = "true"
            data["pile_sn"] = orderRecord.pile_sn,
            data["gun_num"] = orderRecord.gun_num,
            data["openid"] = orderRecord.openid,
            data["out_trade_no"] = orderRecord.out_trade_no,
            data["voltage"] = orderRecord.voltage,
            data["current"] = orderRecord.current,
            data["output_voltage"] = orderRecord.output_voltage,
            data["output_current"] = orderRecord.output_current,
            data["charg_time"] = orderRecord.end_time,
            data["current_readings"] = orderRecord.end_reading,

        return JsonResponse(data)


class OrderErrorView(View):
    def get(self, request, *args, **kwargs):
        errmsg = request.GET.get("errmsg", u"未知错误")
        return render(request, template_name="chargingorder/charging_pile_status.html", context={"errmsg": errmsg})


class OrderChargeStopView(View):
    def post(self, request, *args, **kwargs):
        out_trade_no = request.POST.get("out_trade_no", None)
        pile_sn = request.POST.get("pile_sn", None)
        gun_num = request.POST.get("gun_num", None)
        print(out_trade_no)
        try:
            order = Order.objects.get(out_trade_no=out_trade_no)
            stop_data = {
                "pile_sn": pile_sn,
                "gun_num": int(gun_num),
                "out_trade_no": out_trade_no,
                "consum_money": int(order.consum_money.quantize(decimal.Decimal("0.01")) * 100),
                "total_reading": int(order.get_total_reading() / decimal.Decimal(settings.FACTOR_READINGS)),
                "stop_code": 0,  # 0 主动停止，1被动响应，2消费清单已结束或不存在
                "fault_code": 91    # 用户停止
            }
            # print(stop_data)
            server_send_stop_charging_cmd(**stop_data)
        except Order.DoesNotExist as ex:
            print(ex)
            return JsonResponse({"return_code": "FAIL", "errmsg": "停止操作失败!"})

        return JsonResponse({"return_code": "SUCCESS"})


class OrderView(View):
    """订单"""
    def get(self, request, *args, **kwargs):
        openid = request.session.get("openid", None)
        if openid:
            orders = Order.objects.filter(openid=openid, status=2)[0:50]
        else:
            orders = None

        return render(request, template_name="weixin/user_order_list.html", context={"orders": orders})


class OrderDetailView(DetailView):
    """订单详情"""
    model = Order
    template_name = 'weixin/user_order_detail.html'

