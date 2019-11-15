# coding: utf-8
from django.conf.urls import url, include

from cards.views import CardsStartupView, RechargeMoneyView

urlpatterns = [
    url(r'cards_startup/$', CardsStartupView.as_view(), name='cards-startup'),
    url(r'recharge_money/$', RechargeMoneyView.as_view(), name='recharge-money'),
]