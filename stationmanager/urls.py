"""ChargingStation URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
# from django.contrib import admin
from django.views.generic import TemplateView, RedirectView
from .views import StationListView, StationDetailView, StationPricesDetailView, FaultChargingGunListView

urlpatterns = [
   url(r'^$', StationListView.as_view(), name='station-index'),
   url(r'^detail/(?P<stationid>\d+)/$', StationDetailView.as_view(), name='station-detail'),
   url(r'^pricedetail/(?P<stationid>\d+)/$', StationPricesDetailView.as_view(), name='station-price-detail'),
   url(r'^faultgun/$', FaultChargingGunListView.as_view(), name='fault-gun-list'),
   # url('^logo/$', RedirectView.as_view(url='/static/stationmanager/images/logo-1.png')),
]
