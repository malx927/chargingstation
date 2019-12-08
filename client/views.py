import datetime

from django.shortcuts import render, redirect

from cards.models import CardUser, ChargingCard
from django.urls import reverse
from django.views.generic import ListView


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
    print(user_id, "000000000000000")
    if user_id:
        return render(request, template_name="client/index.html")
    else:
        return redirect(reverse("client:login"))


class CardListView(ListView):
    """充值卡列表"""
    def get(self, request, *args, **kwargs):
        user_id = request.session.get("user_id", None)
        if not user_id:
            return redirect(reverse("client:login"))
        else:
            cards = ChargingCard.objects.filter(user_id=user_id)
            context = {
                "cards": cards
            }
            return render(request, template_name="client/card_list.html", context=context)
