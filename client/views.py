import datetime

from django.db.models import Sum
from django.shortcuts import render, redirect

from cards.models import CardUser, ChargingCard, CardRecharge
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from chargingorder.models import Order


def login(request):
    """
    用户登录
    """
    if request.method == 'POST':
        name = request.POST.get('username')
        password = request.POST.get('password')
        user = CardUser.objects.filter(name=name, password=password).first()
        if not user:
            return render(request, 'client/login.html', {'msg': '用户名或密码错误'})
        elif not user.is_active:
            return render(request, 'client/login.html', {'msg': '用户未激活'})
        else:
            user.last_login = datetime.datetime.now()
            user.save()
            request.session["user_id"] = user.id
            request.session["username"] = user.name
            # init_permission(user, request)
            return redirect(reverse("client:index"))
    else:
        return render(request, 'client/login.html')


def logout(request):
    """
    注销
    :param request:
    :return:
    """
    request.session.delete()

    return redirect(reverse("client:login"))


def index(request):
    user_id = request.session.get("user_id", None)
    if user_id:
        return redirect(reverse("client:card-list"))
    else:
        return redirect(reverse("client:login"))


class CardListView(View):
    """充值卡列表"""
    def get(self, request, *args, **kwargs):
        user_id = request.session.get("user_id", None)
        if not user_id:
            return redirect(reverse("client:login"))
        else:
            search = request.GET.get("search", None)
            queryset = ChargingCard.objects.filter(user_id=user_id)
            if search:
                queryset = queryset.filter(card_num__contains=search)
            context = {
                "cards": queryset
            }
            return render(request, template_name="client/card_list.html", context=context)


class CardRechargeListView(ListView):
    """储蓄卡充值记录"""
    template_name = "client/card_recharge_list.html"
    model = CardRecharge
    context_object_name = "recharges"
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        user_id = request.session.get("user_id", None)
        if not user_id:
            return redirect(reverse("client:login"))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        recharges = CardRecharge.objects.all()
        search = self.request.GET.get("search", None)
        start_date = self.request.GET.get("start_date", None)
        end_date = self.request.GET.get("end_date", None)
        print(search, start_date, end_date)
        if search:
            recharges = recharges.filter(card__card_num__contains=search)

        if start_date and end_date:
            d_start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            d_end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            recharges = recharges.filter(add_time__range=(d_start_date, d_end_date))

        return recharges

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recharges = context.get("recharges")
        total = recharges.aggregate(money=Sum("money"))
        context["total"] = total
        return context


class CardOrderListView(ListView):
    """储蓄卡充电消费记录"""
    template_name = "client/card_order_list.html"
    model = Order
    context_object_name = "orders"
    paginate_by = 2

    def get(self, request, *args, **kwargs):
        user_id = request.session.get("user_id", None)
        if not user_id:
            return redirect(reverse("client:login"))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = context.get("orders")
        total = orders.aggregate(readings=Sum("total_readings"), total_fees=Sum("cash_fee"))
        context["total"] = total
        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        ret = self.get_pagination_data(paginator, page_obj)
        context.update(ret)
        return context

    def get_queryset(self):
        username = self.request.session.get("username", None)

        orders = Order.objects.filter(start_model=1, name=username)

        search = self.request.GET.get("search", None)   # 卡号
        start_date = self.request.GET.get("start_date", None)
        end_date = self.request.GET.get("end_date", None)

        if search:
            orders = orders.filter(openid__contains=search)     # 储值卡充电 openid 存放储值卡卡号

        if start_date and end_date:
            d_start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            d_end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            orders = orders.filter(begin_time__date__range=(d_start_date, d_end_date))

        return orders

    def get_pagination_data(self, paginator, page_obj, diff_count=5):
        page_number = page_obj.number
        num_pages = paginator.num_pages

        left_page_count = 4
        right_page_count = 2
        old_page_range = paginator.page_range
        left_page_range = None
        right_page_range = None
        if len(old_page_range) > diff_count * 2 + left_page_count + right_page_count + 1:
            if page_number - diff_count - left_page_count > 0:
                left_page_range = [p for p in range(1, left_page_count + 1)]
                begin_page = page_number - diff_count
            else:
                begin_page = 1

            if page_number + diff_count + right_page_count < num_pages:
                right_page_range = [p for p in range(num_pages - 1, num_pages + 1)]
                end_page = page_number + diff_count + 1
            else:
                end_page = num_pages + 1

            page_range = [p for p in range(begin_page, end_page)]
        else:
            page_range = old_page_range

        return {
            'page_range': page_range,
            'left_page_range': left_page_range,
            'right_page_range': right_page_range,

        }


class PasswordChangeView(View):
    """修改密码"""
    def get(self, request, *args, **kwargs):
        user_id = request.session.get("user_id", None)
        if not user_id:
            return redirect(reverse("client:login"))
        return render(request, template_name="client/change_password.html")

    def post(self, request, *args, **kwargs):
        user_id = request.POST.get("user_id")
        password = request.POST.get("password")
        password1 = request.POST.get("password1")
        if password != password1:
            msg = "两次密码不一致,请重新输入"
        else:
            CardUser.objects.filter(id=user_id).update(password=password)
            return redirect(reverse("client:login"))

        context = {
            "msg": msg,
        }
        return render(request, template_name="client/change_password.html", context=context)