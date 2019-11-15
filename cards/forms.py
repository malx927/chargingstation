# -*- coding:utf-8 -*-
from cards.models import CardRecharge
from django import forms


class CardRechargeForm(forms.ModelForm):
    """充值卡充值"""
    def __init__(self, *args, **kwargs):
        super(CardRechargeForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CardRecharge
        fields = ["unit_name", "person", "unit_type", "sign_begin", "sign_end", "telephone", "scheme", "address", "lawyer"]

        widgets = {
            'unit_name': forms.TextInput(attrs={'class': "form-control", 'placeholder': '请输入企业名称'}),
            'person': forms.TextInput(attrs={'class': "form-control", 'placeholder': '请输入联系人员'}),
            'sign_begin': forms.TextInput(attrs={'class': "form-control", 'placeholder': '请输入签约开始时间'}),
            'sign_end': forms.TextInput(attrs={'class': "form-control", 'placeholder': '请输入签约结束时间'}),
            'telephone': forms.TextInput(attrs={'class': "form-control", 'placeholder': '请输入联系电话'}),
            'unit_type': forms.Select(attrs={'class': "form-control", 'placeholder': '请选择类型方案'}),
            'scheme': forms.Select(attrs={'class': "form-control", 'placeholder': '请选择签约方案'}),
            'address': forms.TextInput(attrs={'class': "form-control", 'placeholder': '请输入单位地址'}),
            'lawyer': forms.CheckboxSelectMultiple(attrs={'class': "checkbox list-inline"}),

        }

