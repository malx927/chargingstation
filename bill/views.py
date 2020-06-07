import logging
import random

from django.db.models import F
from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
import datetime
from wxchat.models import UserInfo, RechargeRecord
from wxchat.views import order_refund
from .models import UserRefund, UserRefundDetail, WxRefundRecord

logger = logging.getLogger("django")


class ApplyRefundView(View):
    """
    申请退款
    """
    def post(self, request, *args, **kwargs):
        # 个人信息和读取当前余额
        openid = request.session.get("openid", None)
        if openid:
            user = UserInfo.objects.filter(openid=openid).first()
            if user:
                if user.pile_sn:
                    context = {
                        "errmsg": "请充电完毕后,申请退款, 不支持充电中退款申请"
                    }
                    return render(request, template_name="chargingorder/charging_pile_status.html", context=context)
                elif user.is_freeze:
                    context = {
                        "errmsg": "账号已冻结,不能再申请退款"
                    }
                    return render(request, template_name="chargingorder/charging_pile_status.html", context=context)
                else:
                    code = '{0}{1}{2}'.format('S', datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
                    balance = user.total_money - user.consume_money
                    data = {
                        "code": code,
                        "name": user.name,
                        "nickname": user.nickname,
                        "openid": openid,
                        "telephone": user.telephone,
                        "refund_fee": balance
                    }
                    logger.info(data)
                    order_counts = self.get_order_count(openid)
                    print(order_counts)
                    if order_counts == 0:
                        context = {
                            "errmsg": "申请失败, 您一年内没有符合条件的充值订单"
                        }
                        return render(request, template_name="chargingorder/charging_pile_status.html", context=context)

                    logger.info(data)
                    user_refund = UserRefund.objects.create(**data)
                    if user_refund:
                        # 冻结账户
                        user.update_freeze(1, '退款冻结')
                    return render(request, template_name='weixin/user_refund_detail.html', context={"user_refund": user_refund})

        context = {
            "errmsg": "您的账号不存在"
        }
        return render(request, template_name="chargingorder/charging_pile_status.html", context=context)

    def get_order_count(self, openid):
        last_year = datetime.datetime.now() + datetime.timedelta(days=-365)
        order = RechargeRecord.objects.filter(
            openid=openid,
            status=1,
            recharge_type=2,
            pay_time__gt=last_year,
            total_fee__gt=F("refund_fee")
        ).count()
        return order


class ApplyRefundListView(View):
    """订单列表"""
    def get(self, request, *args, **kwargs):
        openid = request.GET.get("openid")
        id = request.GET.get("id")
        print(openid, id)
        # 判断是否生成退款记录
        refund_list = UserRefundDetail.objects.filter(user_refund_id=id)
        if not refund_list.exists():
            # 生成退款数据
            refund = UserRefund.objects.filter(id=id).first()
            order_list = self.get_orders(openid, refund.refund_fee)
            logger.info(order_list)
            refund_list = self.create_refund_order(order_list, refund.id)
        logger.info(refund_list)
        context = {
            "refund_list": refund_list
        }
        return render(request, template_name="bill/user_refund.html", context=context)

    def get_orders(self, openid, balance):
        last_year = datetime.datetime.now() + datetime.timedelta(days=-365)
        orders = RechargeRecord.objects.filter(
            openid=openid,
            status=1,
            recharge_type=2,
            pay_time__gt=last_year,
            total_fee__gte=F("refund_fee")
        ).order_by((F("total_fee") - F("refund_fee")).desc())

        order_list = []
        for order in orders:
            totals = order.total_fee - order.refund_fee

            order_list.append(order)
            if totals >= balance:
                order.refund_money = balance
                return order_list
            else:
                order.refund_money = totals
                balance = balance - totals

        return order_list

    def create_refund_order(self, order_list, user_refund_id):
        for o in order_list:
            out_refund_no = '{0}{1}{2}'.format('T', datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
            data = {
                "out_refund_no": out_refund_no,
                "user_refund_id": user_refund_id,
                "openid": o.openid,
                "out_trade_no": o.out_trade_no,
                "transaction_id": o.transaction_id,
                "total_fee": o.total_fee,
                "refund_fee": o.refund_money,
            }
            logger.info(data)
            UserRefundDetail.objects.create(**data)

        refund_list = UserRefundDetail.objects.filter(user_refund_id=user_refund_id)
        return refund_list


class RefundView(View):
    """
    退款请求
    """
    def post(self, request, *args, **kwargs):
        refund_id = request.POST.get("id", None)
        try:
            user_refund_detail = UserRefundDetail.objects.get(pk=refund_id)
            refund_data = {
                'out_trade_no': user_refund_detail.out_trade_no,
                'out_refund_no': user_refund_detail.out_refund_no,
                'transaction_id': user_refund_detail.transaction_id,
                'total_fee': int(user_refund_detail.total_fee * 100),
                'refund_fee': int(user_refund_detail.refund_fee * 100),
            }
            logger.info(refund_data)
            ret = order_refund(**refund_data)
            logger.info(ret)
            WxRefundRecord.objects.create(**ret)
            if 'return_code' in ret and 'result_code' in ret and ret['return_code'] == 'SUCCESS' and ret['result_code'] == 'SUCCESS':
                user_refund_detail.refund_id = ret["refund_id"]
                user_refund_detail.status = 1
                user_refund_detail.save()
                msg = {
                    "status_code": 201,
                    "message": "用户退款成功"
                }
            else:
                msg = {
                    "status_code": 401,
                    "errmsg": "用户退款失败:{}[{}]".format(ret["return_msg"], ret["err_code_des"])
                }
        except UserRefundDetail.DoesNotExist as ex:
            logger.info(ex)
            msg = {
                "status_code": 401,
                "errmsg": "订单不存在"
            }
            logger.info(ex)

        return JsonResponse(msg)
