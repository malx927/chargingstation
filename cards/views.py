from cards.forms import CardRechargeForm
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


class RechargeMoneyView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        c_id = request.GET.get("c_id")
        card = ChargingCard.objects.filter(pk=c_id).first()
        inital = {}
        if card:
            inital["card"] = [card.id]
            if card.user:
                inital["user"] = [card.user_id]
            form = CardRechargeForm(initial={"card": [card.id, ], "user": [card.user_id,]})
        else:
            form = None

        context = {
            "form": form,
            "action": request.get_full_path()
        }

        return render(request, template_name="cards/card_recharge.html", context=context)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):

        form = CardRechargeForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.op_user = request.user
            instance.save()
            money = instance.card.money
            instance.card.money = money + instance.money
            instance.card.save()
        return redirect("/ydadmin/cards/chargingcard/")