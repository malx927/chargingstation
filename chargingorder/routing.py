# coding=utf-8

from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/recharge/(?P<pile_sn>[\w-]+)/(?P<gun_num>\d+)/$', consumers.ChargingConsumer),
]
