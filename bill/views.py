import logging
import random

from django.shortcuts import render
from django.views import View
import datetime
from wxchat.models import UserInfo, RechargeRecord
from .models import UserRefund

logger = logging.getLogger("django")


class ApplyRefund(View):
    """
    申请退款
    """
    def post(self, request, *args, **kwargs):
        # 个人信息和读取当前余额
        openid = request.session.get("openid", None)
        openid = 'oX5Zn04Imn5RlCGlhEVg-aEUCHNs'
        if openid:
            user = UserInfo.objects.filter(openid=openid).first()
            if user:
                if user.pile_sn:
                    context = {
                        "errmsg": "请充电完毕后,申请退款, 不支持充电中退款申请"
                    }
                    return render(request, template_name="chargingorder/charging_pile_status.html", context=context)
                else:
                    out_refund_no = '{0}{1}{2}'.format('T', datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
                    balance = user.total_money - user.consume_money
                    data = {
                        "out_refund_no": out_refund_no,
                        "name": user.name,
                        "nickname": user.nickname,
                        "openid": openid,
                        "telephone": user.telephone,
                        "refund_fee": balance
                    }
                    logger.info(data)
                    recharge_order = self.get_old_order(openid, balance)
                    print(recharge_order)
                    if recharge_order is None:
                        context = {
                            "errmsg": "申请失败!"
                        }
                        return render(request, template_name="chargingorder/charging_pile_status.html", context=context)
                    else:
                        data["out_trade_no"] = recharge_order.out_trade_no
                        data["transaction_id"] = recharge_order.transaction_id
                        data["total_fee"] = recharge_order.cash_fee
                        data["total_fee111"] = recharge_order.cash_fee
                    logger.info(data)
                    user_refund = UserRefund.objects.create(**data)
                    if user_refund:
                        # 冻结账户
                        user.update_freeze(1, '退款冻结')
                    return render(request, template_name='weixin/user_refund_detail.html', context={"refund": user_refund})

        context = {
            "errmsg": "您的账号不存在"
        }
        return render(request, template_name="chargingorder/charging_pile_status.html", context=context)

    def get_old_order(self, openid, balance):
        last_year = datetime.datetime.now() + datetime.timedelta(days=-365)
        order = RechargeRecord.objects.filter(
            openid=openid,
            status=1,
            recharge_type=2,
            pay_time__gt=last_year,
            cash_fee__gte=balance
        ).first()
        return order
