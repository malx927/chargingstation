# -*-coding:utf-8-*-
import json
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from .models import UserInfo

__author__ = 'malxin'
from django.conf import settings
from wechatpy.oauth import WeChatOAuth


def weixin_decorator(func):
    def wrapper(request, *args, **kwargs):
        code = request.GET.get('code', None)
        openid = request.session.get('openid', None)
        print("weixin_decorator", code, openid)
        if openid is None:
            if code is None:  # 获取授权码code
                redirect_url = '%s://%s%s' % (request.scheme, request.get_host(), request.get_full_path())
                webchatOAuth = WeChatOAuth(settings.WECHAT_APPID, settings.WECHAT_SECRET, redirect_url, 'snsapi_userinfo')
                authorize_url = webchatOAuth.authorize_url
                return HttpResponseRedirect(authorize_url)
            else:  # 同意授权，通过授权码获取ticket,根据ticket拉取用户信息
                webchatOAuth = WeChatOAuth(settings.WECHAT_APPID, settings.WECHAT_SECRET, '', 'snsapi_userinfo')
                res = webchatOAuth.fetch_access_token(code)
                if 'errcode' in res:
                    return HttpResponse(json.dumps(res))
                else:
                    open_id = webchatOAuth.open_id
                    userinfo = webchatOAuth.get_user_info()
                    userinfo.pop('privilege')
                    obj, created = UserInfo.objects.update_or_create(openid=open_id, defaults=userinfo)
                    print('-------------', obj, created)
                    request.session['openid'] = open_id
                    request.session['nickname'] = obj.nickname
                    request.session['headimgurl'] = obj.headimgurl
                    request.session["created"] = created
                    if not created:
                        request.session["username"] = obj.name
                        request.session["car_type"] = obj.car_type
                    return func(request, *args, **kwargs)
        else:
            return func(request, *args, **kwargs)
    return wrapper
