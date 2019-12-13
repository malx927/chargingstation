# -*-coding:utf-8-*-
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
from .views import index, login, logout, CardListView, CardRechargeListView, CardOrderListView, PasswordChangeView

urlpatterns = [
    url(r'^$', index, name="index"),  # 客户端入口
    url(r'^login/$', login, name="login"),  # 登录窗口
    url(r'^logout/$', logout, name="logout"),  # 登录窗口
    url(r'^change_password/$', PasswordChangeView.as_view(), name="password-change"),  # 修改密码
    url(r'^card_list/$', CardListView.as_view(), name="card-list"),  # 充值卡列表
    url(r'^card_recharge_list/$', CardRechargeListView.as_view(), name="card-recharge-list"),  # 储值卡充值记录列表
    url(r'^card_order_list/$', CardOrderListView.as_view(), name="card-order-list"),  # 储值卡充值消费记录
]
