import random

from django.shortcuts import render
from django.views import View
import datetime
from wxchat.models import UserInfo, RechargeRecord
from .models import UserRefund


class ApplyRefund(View):
    """
    申请退款
    """
    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        # 个人信息和读取当前余额
        openid = request.session.get("openid", None)
        if openid:
            user = UserInfo.objects.filter(openid=openid).first()
            if user:
                out_refund_no = '{0}{1}{2}'.format('T', datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(10000, 100000))
                balance = user.total_money - user.consume_money
                data = {
                    "out_refund_no": out_refund_no,
                    "name": user.name,
                    "nickname": user.nickname,
                    "openid": openid,
                    "refund_fee": balance
                }

                recharge_order = self.get_old_order(openid, balance)
                if recharge_order:
                    data["out_trade_no"] = recharge_order.out_trade_no
                    data["transaction_id"] = recharge_order.transaction_id
                    data["total_fee"] = recharge_order.cash_fee
                user_refund = UserRefund.objects.create(**data)
                return render(request, template_name='wxchat/register.html', context={"refund": user_refund})

        return render(request, template_name='wxchat/register.html')

    def get_old_order(self, openid, balance):
        user_balance = int(balance * 100)
        last_year = datetime.datetime.now() + datetime.timedelta(days=-365)
        order = RechargeRecord.objects.filter(
            openid=openid,
            status=1,
            recharge_type=2,
            pay_time__lt=last_year,
            cash_fee__gte=user_balance
        ).first()
        return order
