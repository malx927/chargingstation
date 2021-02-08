# coding=utf-8
from django.conf.urls import url, include

from django.views.generic import TemplateView
from wxchat.views import OrderPayView, pay_notify

from .views import ArticleView, ArticleDetailView

urlpatterns = [
   url(r'^$', ArticleView.as_view(), name='article-index'),
   url(r'article/(?P<pk>\d+)/$', ArticleDetailView.as_view(), name='article-detail'),

]
