# -*-coding:utf-8-*-
import decimal
import logging
import random
import time
from datetime import datetime
import json

from chargingorder.models import Order
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django import forms
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from io import BytesIO

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
from wxchat.forms import RegisterForm, SubAccountForm
from stationmanager.utils import create_qrcode
from .models import UserInfo, RechargeRecord, WxUnifiedOrderResult, WxPayResult, RechargeList, UserCollection, \
    SubAccount

logger = logging.getLogger("django")

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
    # wxPay = WeChatPay(appid=settings.WECHAT_APPID, api_key=settings.MCH_KEY, mch_id=settings.MCH_ID)
    wxPay = WeChatPay(appid=settings.WECHAT_APPID, api_key=settings.MCH_KEY,
                      mch_id=settings.MCH_ID, mch_cert=settings.API_CLIENT_CERT_PATH,
                      mch_key=settings.API_CLIENT_KEY_PATH)
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


# 退款
def order_refund(*arg, **kwargs):
    transaction_id = kwargs.get('transaction_id', '')
    out_trade_no = kwargs.get('out_trade_no', '')
    out_refund_no = kwargs.get('out_refund_no', '')
    total_fee = kwargs.get('total_fee', 0)
    refund_fee = kwargs.get('refund_fee', 0)
    if total_fee == 0 or refund_fee == 0:
        return None
    wxPay = WeixinPay()
    ret = wxPay.refund.apply(total_fee=total_fee, refund_fee=refund_fee, out_trade_no=out_trade_no, transaction_id=transaction_id, out_refund_no=out_refund_no)

    return ret


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
                "name": "附近电站",
                "url": settings.ROOT_URL + "/station/"
            },
            # {
            #     "type": "view",
            #     "name": "充电桩",
            #     "url": settings.ROOT_URL + "/order/"
            # },
            {
                "type": "view",
                "name": "扫码充电",
                "url": settings.ROOT_URL + "/wechat/scanqrcode/"
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
            logger.info(errors)
            return HttpResponse(json.dumps(errors))

        out_trade_no = '{0}{1}{2}{3}'.format('P', settings.MCH_ID, datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
        recharge_type = 2       # 微信支付
        order_data = {
            "out_trade_no": out_trade_no,
            "openid": openid,
            "total_fee": int(money),
            "recharge_type": recharge_type,
        }
        logger.info(order_data)
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
            logger.info(save_data)
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
            logger.info(errors)
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
        logger.info(res_data)
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

                coupon_fee_0 = res_data.get('coupon_fee_0', 0) / 100
                coupon_fee_1 = res_data.get('coupon_fee_1', 0) / 100

                data = {
                    "openid": openid,
                    "name": name,
                    "total_fee": res_data['total_fee'] / 100,
                    "transaction_id": res_data['transaction_id'],
                    "cash_fee": cash_fee + coupon_fee_0 + coupon_fee_1,
                    "status": 1,
                    "pay_time": pay_time,
                    "recharge_type": 2,     # 微信支付
                }
                logger.info(data)
                RechargeRecord.objects.update_or_create(defaults=data, out_trade_no=out_trade_no)

                try:
                    user = UserInfo.objects.get(openid=openid)
                    if user.out_trade_no != out_trade_no:
                        user.total_money += decimal.Decimal(cash_fee)
                        user.out_trade_no = out_trade_no
                        user.last_charg_time = datetime.now()
                        user.save(update_fields=["total_money", "out_trade_no", "last_charg_time"])
                        # 订单同步余额
                        if user.out_trade_no:
                            balance = user.account_balance()
                            Order.objects.filter(out_trade_no=user.out_trade_no, status__lt=2).update(balance=balance)
                except UserInfo.DoesNotExist as ex:
                    values = {
                        "openid": openid,
                        "nickname": name,
                        "total_money": cash_fee,
                        "out_trade_no": out_trade_no,
                        "last_charg_time": datetime.now()
                    }
                    logger.info(values)
                    user = UserInfo.objects.create(**values)
                # 发送模板消息给客户
                # sendTempMessageToUser(order)
        return HttpResponse(xml)
    except InvalidSignatureException as error:
        logger.info(error)


class RegisterView(View):
    """
    用户登记完整信息
    """
    def get(self, request, *args, **kwargs):
        openid = request.session.get("openid", None)
        try:
            user = UserInfo.objects.get(openid=openid)
        except UserInfo.DoesNotExist as ex:
            user = None

        url = request.GET.get("url", None)
        if url is None:
            url = reverse("wxchat-personinfo")
            print(url)
        context = {
            "openid": openid,
            "url": url,
            "user": user,
        }

        return render(request, template_name='wxchat/register.html', context=context)

    def post(self, request, *args, **kwargs):
        form = RegisterForm(request.POST or None)
        url = request.POST.get("url", None)

        if form.is_valid():
            openid = form.cleaned_data["openid"]
            user_name = form.cleaned_data["user_name"]
            telephone = form.cleaned_data["telephone"]
            car_number = form.cleaned_data["car_number"]
            car_type = form.cleaned_data["car_type"]
            print(user_name, telephone, car_number, car_type, openid)
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
        order = None
        try:
            openid = request.session.get("openid", None)
            user = UserInfo.objects.get(openid=openid)
            order = Order.objects.filter(out_trade_no=user.out_trade_no, charg_status_id__gt=0, charg_status_id__lt=7).first()
        except UserInfo.DoesNotExist as ex:
            user = None

        signPackage = getJsApiSign(self.request)
        context = {
            "user": user,
            "sign": signPackage,
            "order": order,
        }
        return render(request, template_name="weixin/wxchat_personinfo.html", context=context)


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


class UserDetailView(View):

    def get(self, request, *args, **kwargs):
        try:
            user_id = kwargs.get("id", None)
            user = UserInfo.objects.get(pk=user_id)
        except UserInfo.DoesNotExist as ex:
            logger.info(ex)
            user = None
        context = {
            "user": user,
        }
        return render(request, template_name="weixin/user_info_detail.html", context=context)


class UserBalanceView(View):

    def get(self, request, *args, **kwargs):
        context = {}
        try:
            user_id = kwargs.get("id", None)
            user = UserInfo.objects.get(pk=user_id)
            openid = user.openid
            recharge_result = RechargeRecord.objects.filter(openid=openid).aggregate(recharge_totals=Sum("cash_fee"))
            consum_result = Order.objects.filter(openid=openid, status=2, cash_fee__gt=0).aggregate(consum_totals=Sum("cash_fee"))
            context = {
                "user": user,
                "recharge_totals": recharge_result["recharge_totals"],
                "consum_result": consum_result["consum_totals"],
            }
        except UserInfo.DoesNotExist as ex:
            print("用户不存在")

        return render(request, template_name="weixin/my_balance.html", context=context)


class UserCollectionView(View):
    """我的收藏"""
    def get(self, request, *args, **kwargs):
        openid = request.session.get("openid", None)
        if openid:
            collections = UserCollection.objects.filter(openid=openid)
        else:
            collections = None
        sign = getJsApiSign(request)
        context = {
            "collections": collections,
            "sign": sign,
        }
        return render(request, template_name="weixin/user_collection.html", context=context)


class UserQRCodeView(View):
    """客户二维码"""
    def get(self, request, *args, **kwargs):
        openid = request.GET.get("openid", None)
        if openid:
            image = create_qrcode(openid)
            f = BytesIO()
            image.save(f, "PNG")
            return HttpResponse(f.getvalue())
        else:
            return HttpResponse()


class ShowUserQRCodeView(View):
    """显示客户二维码"""
    def get(self, request, *args, **kwargs):
        openid = request.session.get("openid", "")
        context = {
            "openid": openid,
        }

        return render(request, template_name="weixin/my_qrcode.html", context=context)


class SubAccountView(View):
    """附属账号"""
    def get(self, request, *args, **kwargs):
        openid = request.session.get("openid", None)
        if openid:
            sub_accounts = SubAccount.objects.filter(main_user__openid=openid)
            print(sub_accounts)
        else:
            sub_accounts = None
        sign = getJsApiSign(request)
        context = {
            "sub_accounts": sub_accounts,
            "sign": sign,
        }
        return render(request, template_name="weixin/sub_account.html", context=context)

    def post(self, request, *args, **kwargs):
        sub_openid = request.POST.get("openid", None)
        openid = request.session.get("openid", None)
        context = {
            "success": "false",
        }
        if openid and sub_openid:
            try:
                SubAccount.objects.get(sub_user__openid=sub_openid)
            except SubAccount.DoesNotExist as ex:
                try:
                    sub_user = UserInfo.objects.get(openid=sub_openid)
                    user = UserInfo.objects.get(openid=openid)
                    sub_account = SubAccount()
                    sub_account.sub_user = sub_user
                    sub_account.main_user = user
                    sub_account.save()
                    context["success"] = "true"
                except UserInfo.DoesNotExist as ex:
                    print(ex)
        return JsonResponse(context)


class UpdateUserName(View):
    """修改姓名"""
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get("user_id", None)
        try:
            user = UserInfo.objects.get(id=user_id)
        except UserInfo.DoesNotExist as ex:
            user = None

        context = {
            "user": user,
        }
        return render(request, template_name="weixin/update_user_name.html", context=context)

    def post(self, request, *args, **kwargs):
        user_name = request.POST.get("user_name", None)
        user_id = request.POST.get("user_id", None)
        if user_name:
            UserInfo.objects.filter(id=user_id).update(name=user_name)

        return HttpResponseRedirect(reverse("wxchat-sub-account"))


class DelSubAccountView(View):
    """删除附加用户"""
    def post(self, request, *args, **kwargs):
        account_id = request.POST.get("account_id")
        ret = SubAccount.objects.filter(id=account_id).delete()
        context = {
            "success": "false",
        }
        if ret[0] > 0:
            context["success"] = "true"

        return JsonResponse(context)


class SubAccountUpdateAmount(View):
    """用户分配金额"""
    def get(self, request, *args, **kwargs):
        try:
            openid = request.session.get("openid")
            owner = UserInfo.objects.get(openid=openid)
            sub_users = SubAccount.objects.filter(main_user__openid=openid).values("id", "sub_user", "recharge_amount", "balance")
            SubAccountFormSet = forms.formset_factory(SubAccountForm, extra=0)
            formset = SubAccountFormSet(initial=sub_users)
        except UserInfo.DoesNotExist as ex:
            owner = None
            formset = None

        context = {
            "owner": owner,
            "formset": formset,
        }
        return render(request, template_name="weixin/sub_user_input_money.html", context=context)

    def post(self, request, *args, **kwargs):
        pass
        # SubAccountFormSet = forms.formset_factory(SubAccountForm, extra=0)
        # formset = SubAccountFormSet(request.POST)
        # if formset.is_valid():
        #     for row in formset.cleaned_data:
        #         # 删除字典携带的id
        #         id = row.pop('id')
        #         SubAccount.objects.filter(id=id).update(**row)
        #
        # return render(request, 'index.html', {'formset': formset})


class UserBalanceResetView(View):
    """用户账号清零"""
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get("user_id")
        user = UserInfo.objects.filter(pk=user_id).first()

        context = {
            "user": user,
            "action": request.get_full_path()
        }
        return render(request, template_name="wxchat/user_balance_reset.html", context=context)


class RefundView(View):
    """
    退款请求
    """
    def get(self, request, *args, **kwargs):
        out_trade_no = request.GET.get("out_trade_no", None)
        change_list = request.GET.get("change_list", None)
        record = RechargeRecord.objects.filter(out_trade_no=out_trade_no).first()
        if record:
            out_refund_no = '{0}{1}{2}'.format('T', datetime.now().strftime('%Y%m%d%H%M%S'),
                                              random.randint(10000, 100000))
            refund_data = {
                'out_trade_no': record.out_trade_no,
                'out_refund_no': out_refund_no,
                'total_fee': int(record.total_fee * 100),
                'refund_fee': int(record.cash_fee * 100),
            }
            logger.info(refund_data)
            ret = order_refund(**refund_data)
            logger.info(ret)

        return HttpResponseRedirect(change_list)


