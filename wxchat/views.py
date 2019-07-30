# -*-coding:utf-8-*-
import decimal
import random
import time
from datetime import datetime
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from django.views.decorators.csrf import csrf_exempt
from redis import Redis
from wechatpy import parse_message, create_reply, WeChatClient, WeChatPay
from wechatpy.exceptions import InvalidSignatureException, WeChatPayException
from wechatpy.pay import dict_to_xml
from wechatpy.replies import TransferCustomerServiceReply, ImageReply, VoiceReply
from wechatpy.session.redisstorage import RedisStorage
from wechatpy.utils import check_signature, random_string
from chargingstation import settings
from wxchat.decorators import weixin_decorator
from wxchat.forms import RegisterForm
from .models import UserInfo, RechargeRecord, WxUnifiedOrderResult, WxPayResult, RechargeList

redis_client = Redis.from_url(settings.REDIS_URL)
session_interface = RedisStorage(
    redis_client,
    prefix="wechatpy"
)


def wxClient():
    """
    创建微信客户端对象
    :return:
    """
    client = WeChatClient(settings.WECHAT_APPID, settings.WECHAT_SECRET, session=session_interface)
    return client


def WeixinPay():
    """
     创建微信支付对象
    :return:
    """
    wxPay = WeChatPay(appid=settings.WECHAT_APPID, api_key=settings.MCH_KEY, mch_id=settings.MCH_ID)
    return wxPay


def getJsApiSign(request):
    """
    微信JSAPI支付
    """
    client = wxClient()
    ticket = client.jsapi.get_jsapi_ticket()
    noncestr = random_string(15)
    timestamp = int(time.time())
    url = request.build_absolute_uri()
    signature = client.jsapi.get_jsapi_signature(noncestr, ticket, timestamp, url)
    sign_package = {
        "appId": settings.WECHAT_APPID,
        "nonceStr": noncestr,
        "timestamp": timestamp,
        "signature": signature
    }
    return sign_package


@csrf_exempt
def wechat(request):
    if request.method == 'GET':
        signature = request.GET.get('signature', None)
        timestamp = request.GET.get('timestamp', None)
        nonce = request.GET.get('nonce', None)
        echostr = request.GET.get('echostr', None)

        try:
            check_signature(settings.WECHAT_TOKEN, signature, timestamp, nonce)
        except InvalidSignatureException:
            echostr = 'error'

        return HttpResponse(echostr)

    elif request.method == 'POST':
        msg = parse_message(request.body)
        if msg.type == 'text':
            reply = TransferCustomerServiceReply(message=msg)
        elif msg.type == 'image':
            reply = ImageReply(message=msg)
            reply.media_id = msg.media_id
        elif msg.type == 'voice':
            reply = VoiceReply(message=msg)
            reply.media_id = msg.media_id
            reply.content = '语音信息'
        elif msg.type == 'event':
            print('eventkey=', msg.event)
            if msg.event == 'subscribe':
                saveUserinfo(msg.source)
                reply = create_reply('你好，欢迎关注亚电新能源', msg)
            elif msg.event == 'unsubscribe':
                reply = create_reply('取消关注公众号', msg)
                unSubUserinfo(msg.source)
            elif msg.event == 'subscribe_scan':
                reply = create_reply('你好，欢迎关注亚电新能源', msg)
                saveUserinfo(msg.source, msg.scene_id)
            elif msg.event == 'scan':
                reply = create_reply('', msg)
            else:
                reply = create_reply('view', msg)
        else:
            reply = create_reply('', msg)

        response = HttpResponse(reply.render(), content_type="application/xml")
        return response


def saveUserinfo(openid, scene_id=None):
    """
    保存或更新关注用户信息
    :param openid:
    :param scene_id:
    :return:
    """
    client = wxClient()
    user = client.user.get(openid)
    if 'errcode' not in user:
        user.pop('groupid')
        user.pop('qr_scene_str')
        user.pop('remark')
        user.pop('tagid_list')
        sub_time = user.pop('subscribe_time')
        sub_time = datetime.fromtimestamp(sub_time)
        user['subscribe_time'] = sub_time
        obj, created = UserInfo.objects.update_or_create(defaults=user, openid=openid)
    else:
        print(user)


def unSubUserinfo(openid):
    """
    取消订阅
    :param openid:
    :return:
    """
    try:
        user = UserInfo.objects.get(openid=openid)
        if user:
            # 是否应该保存历史信息
            user.subscribe = 0
            user.save()
    except UserInfo.DoesNotExist:
        pass


@login_required
def createMenu(request):
    client = wxClient()
    resp = client.menu.create({
        "button": [
            {
                "type": "view",
                "name": "充电桩",
                "url": settings.ROOT_URL + "/order/"
            },
            {
                "type": "view",
                "name": "充电站",
                "url": settings.ROOT_URL + "/station/"
            },
            {
                "type": "view",
                "name": "个人中心",
                "url": settings.ROOT_URL + "/wechat/personinfo/"
            },

        ]
    })
    return HttpResponse(json.dumps(resp))


@login_required
def deleteMenu(request):
    client = wxClient()
    resp = client.menu.delete()
    return HttpResponse(json.dumps(resp))


@login_required
def getMenu(request):
    client = wxClient()
    resp = client.menu.get()
    return HttpResponse(json.dumps(resp, ensure_ascii=False))


class OrderPayView(View):
    """
    充值支付
    """
    def get(self, request, *args, **kwargs):
        openid = request.session.get("openid", None)
        url = request.GET.get("url", None)
        lists = RechargeList.objects.all()
        signPackage = getJsApiSign(self.request)
        context = {
            "openid": openid,
            "url": url,
            "sign": signPackage,
            "lists": lists,
        }
        # return render(request, template_name="wxchat/wxchat_pay.html", context=context)
        return render(request, template_name="wxchat/recharge_list.html", context=context)

    def post(self, request, *args, **kwargs):
        trade_type ='JSAPI'
        body = '充电桩充值'
        # 获得订单信息
        money = request.POST.get('money', '0')
        openid = request.session.get('openid', None)
        attach = request.POST.get("attach", None)

        if money is None or int(money) <= 0:
            errors = {
                'return_code': "FAIL",
                'return_msg': u"请输入充值金额",
            }
            return HttpResponse(json.dumps(errors))

        out_trade_no = '{0}{1}{2}{3}'.format('P', settings.MCH_ID, datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
        recharge_type = 2       # 微信支付
        order_data = {
            "out_trade_no": out_trade_no,
            "openid": openid,
            "total_fee": int(money),
            "recharge_type": recharge_type,
        }
        order = RechargeRecord.objects.create(**order_data)
        if order:
            total_fee = int(order.total_fee * 100)
        else:
            errors = {
                'return_code': "FAIL",
                'return_msg': u"订单不存在",
            }
            return HttpResponse(json.dumps(errors))

        try:
            wxPay = WeixinPay()
            if openid == 'o6Lcy5jOuH-efHvQJPyGFIw7PbGA':
                total_fee = 1
            data = wxPay.order.create(trade_type=trade_type, body=body, total_fee=total_fee, out_trade_no=out_trade_no, attach=attach, notify_url=settings.NOTIFY_URL, user_id=openid)
            prepay_id = data.get('prepay_id', None)
            save_data = dict(data)
            # 保存统一订单数据
            WxUnifiedOrderResult.objects.create(**save_data)
            if prepay_id:
                return_data = wxPay.jsapi.get_jsapi_params(prepay_id=prepay_id, jssdk=True)
                return HttpResponse(json.dumps(return_data))
            else:
                print(data)
        except WeChatPayException as wxe:
            errors = {
                'return_code': wxe.return_code,
                'result_code': wxe.result_code,
                'return_msg':  wxe.return_msg,
                'errcode':  wxe.errcode,
                'errmsg':   wxe.errmsg
            }
            RechargeRecord.objects.filter(out_trade_no=out_trade_no).delete()
            return HttpResponse(json.dumps(errors))


def get_order(openid, out_trade_no):
    """
    确定订单是否有效
    :param user_id:
    :param out_trade_no:
    :return:
    """
    try:
        order = RechargeRecord.objects.get(openid=openid, out_trade_no=out_trade_no, status=0)
    except RechargeRecord.DoesNotExist as ex:
        order = None
    return order


# 查询微信订单是否存在
def query_order(transaction_id, out_trade_no):
    wxPay = WeixinPay()
    order_data = wxPay.order.query(transaction_id=transaction_id, out_trade_no=out_trade_no)
    data = dict(order_data)
    if 'return_code' in data and 'result_code' in data and data['return_code'] == 'SUCCESS' and data['result_code'] == 'SUCCESS':
        return True
    else:
        return False


@csrf_exempt
def pay_notify(request):
    try:
        wxPay = WeixinPay()
        result_data = wxPay.parse_payment_result(request.body)  # 签名验证
        # 保存支付成功返回数据
        res_data = dict(result_data)
        WxPayResult.objects.create(**res_data)
        # 查询订单,判断是否正确
        transaction_id = res_data.get('transaction_id', None)
        out_trade_no = res_data.get('out_trade_no', None)
        openid = res_data.get('openid', None)

        retBool = query_order(transaction_id, out_trade_no)    # 查询订单

        data = {
            'return_code': result_data.get('return_code'),
            'return_msg': result_data.get('return_msg')
        }
        xml = dict_to_xml(data, '')
        if not retBool:  # 订单不存在
            return HttpResponse(xml)
        else:
            # 验证金额是否一致
            if 'return_code' in res_data and 'result_code' in res_data and res_data['return_code'] == 'SUCCESS' and res_data['result_code'] == 'SUCCESS':
                time_end = res_data['time_end']
                pay_time = datetime.strptime(time_end, "%Y%m%d%H%M%S")
                try:
                    user = UserInfo.objects.get(openid=openid)
                    name = user.name if user.name else user.nickname
                except UserInfo.DoesNotExist as ex:
                    name = ''

                cash_fee = res_data['cash_fee'] / 100
                data = {
                    "openid": openid,
                    "name": name,
                    "total_fee": res_data['total_fee'] / 100,
                    "transaction_id": res_data['transaction_id'],
                    "cash_fee": cash_fee,
                    "status": 1,
                    "pay_time": pay_time,
                    "recharge_type": 2,     # 微信支付
                }

                RechargeRecord.objects.update_or_create(defaults=data, out_trade_no=out_trade_no)

                try:
                    user = UserInfo.objects.get(openid=openid)
                    if user.out_trade_no != out_trade_no:
                        user.total_money += decimal.Decimal(cash_fee)
                        user.out_trade_no = out_trade_no
                        user.last_charg_time = datetime.now()
                        user.save(update_fields=["total_money", "out_trade_no", "last_charg_time"])
                except UserInfo.DoesNotExist as ex:
                    values = {
                        "openid": openid,
                        "nickname": name,
                        "total_money": cash_fee,
                        "out_trade_no": out_trade_no,
                        "last_charg_time": datetime.now()
                    }
                    user = UserInfo.objects.create(**values)
                # 发送模板消息给客户
                # sendTempMessageToUser(order)
        return HttpResponse(xml)
    except InvalidSignatureException as error:
        print(error)


class RegisterView(View):
    """
    用户登记完整信息
    """
    def get(self, request, *args, **kwargs):
        openid = request.session.get("openid", None)
        url = request.GET.get("url", None)
        return render(request, template_name='wxchat/register.html', context={"openid": openid, "url": url})

    def post(self, request, *args, **kwargs):
        form = RegisterForm(request.POST or None)
        url = request.POST.get("url", None)

        if form.is_valid():
            openid = form.cleaned_data["openid"]
            user_name = form.cleaned_data["user_name"]
            telephone = form.cleaned_data["telephone"]
            car_number = form.cleaned_data["car_number"]
            car_type = form.cleaned_data["car_type"]
            print(user_name, telephone, car_number, car_type,openid)
            UserInfo.objects.filter(openid=openid).update(name=user_name, telephone=telephone, car_number=car_number, car_type=car_type)
            request.session["created"] = False
            request.session["username"] = user_name
        else:
            errors = form.errors
            print(errors, 'errors')
            context = {
                "form": form,
                "errors": errors
            }
            return render(request, template_name="wxchat/register.html", context=context)

        return HttpResponseRedirect(url)


class PersonInfoView(View):
    """个人信息"""
    @method_decorator(weixin_decorator)
    def get(self, request, *args, **kwargs):
        try:
            openid = request.session.get("openid", None)
            user = UserInfo.objects.get(openid=openid)
        except UserInfo.DoesNotExist as ex:
            user = None
        signPackage = getJsApiSign(self.request)
        context = {
            "user": user,
            "sign": signPackage
        }
        return render(request, template_name="wxchat/wxchat_personinfo.html", context=context)

    def post(self, request, *args, **kwargs):
        pass


class OrderRemoveView(View):
    """删除未支付的订单"""
    def post(self, request, *args, **kwargs):
        openid = request.POST.get("openid", None)
        if openid:
            ret = RechargeRecord.objects.filter(openid=openid, status=0).delete()
            print("OrderRemoveView:", ret)
        return HttpResponse("success")


class ScanQRCodeView(View):
    """二维码扫描"""
    def get(self, request, *args, **kwargs):
        signPackage = getJsApiSign(self.request)
        context = {
            "sign": signPackage
        }
        return render(request, template_name="weixin/charging_qrcode.html", context=context)