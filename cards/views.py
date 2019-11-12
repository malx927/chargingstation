from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View


# @login_required
from cards.models import ChargingCard


class CardsStartupView(View):
    """储值卡"""
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        status = request.GET.get("status")
        c_id = request.GET.get("c_id")
        ChargingCard.objects.filter(pk=c_id).update(status=status)
        return redirect("/ydadmin/cards/chargingcard/")