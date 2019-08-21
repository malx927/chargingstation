# coding=utf-8

from django import forms

from wxchat.models import SubAccount, UserInfo


class RegisterForm(forms.Form):
    """
    用户注册
    """
    user_name = forms.CharField()
    telephone = forms.CharField()
    openid = forms.CharField()
    car_number = forms.CharField()
    car_type = forms.CharField()


class SubAccountForm(forms.Form):
    id = forms.IntegerField(required=True)
    sub_user = forms.ModelChoiceField(queryset=SubAccount.objects.all())
    recharge_amount = forms.DecimalField(max_digits=7, decimal_places=2)
    balance = forms.DecimalField(max_digits=7, decimal_places=2)

