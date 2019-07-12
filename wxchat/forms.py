# coding=utf-8

from django import forms


class RegisterForm(forms.Form):
    """
    用户注册
    """
    user_name = forms.CharField()
    telephone = forms.CharField()
    openid = forms.CharField()

