# coding: utf-8
from django.conf.urls import url, include

from cards.views import CardsStartupView

urlpatterns = [
    url(r'cards_startup/$', CardsStartupView.as_view(), name='cards-startup'),
]