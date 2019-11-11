# coding= utf8
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
# from django.contrib import admin
# from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token
from rest_framework.authtoken import views
from django.views.generic import TemplateView, RedirectView
import xadmin
xadmin.autodiscover()

from xadmin.plugins import xversion
xversion.register_models()

urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    url(r'^ydadmin/', include(xadmin.site.urls)),
    url(r'^api/auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/', views.obtain_auth_token),
    # url(r'^api/token/auth/', obtain_jwt_token),
    # url(r'^api/token/refresh/', refresh_jwt_token),
    # url(r'^api/token/verify/', verify_jwt_token),
    url(r'^station/', include('stationmanager.urls')),
    url(r'^station/api/', include('stationmanager.api.urls')),
    url(r'^order/', include('chargingorder.urls')),
    url(r'^order/api/', include('chargingorder.api.urls')),
    url(r'^wechat/', include('wxchat.urls')),
    url(r'^wechat/api/', include('wxchat.api.urls')),
    url(r'^evcs/v20190507/', include('echargenet.urls')),
    url(r'^MP_verify_6ZHqlaeJeyI9V6QU\.txt$', TemplateView.as_view(template_name='MP_verify_6ZHqlaeJeyI9V6QU.txt', content_type='text/plain')),
    url('^favicon\.ico$', RedirectView.as_view(url='static/favicon.ico')),
    url('^stats/', include("statistic.urls")),
    url('^cards/', include("cards.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
