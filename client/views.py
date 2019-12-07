import datetime

from django.shortcuts import render, redirect

from cards.models import CardUser
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
            return redirect(index)
    else:
        return render(request, 'client/login.html')


def logout(request):
    """
    注销
    :param request:
    :return:
    """
    request.session.delete()

    return redirect('/login/')


def index(request):
    user_id = request.session.get("user_id", None)
    if user_id:
        return render(request, template_name="client/index.html")
    else:
        return redirect(reverse("index"))


class CardListView(ListView):
    pass