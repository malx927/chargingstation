# -*- coding:utf-8 -*-
from cards.models import CardRecharge
from django import forms


class CardRechargeForm(forms.ModelForm):
    """充值卡充值"""
    def __init__(self, *args, **kwargs):
        super(CardRechargeForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CardRecharge
        fields = ["card", "face_num", "name", "money"]

        widgets = {
            'card': forms.TextInput(attrs={'class': "form-control", "readonly": "true"}),
            'face_num': forms.TextInput(attrs={'class': "form-control", "readonly": "true"}),
            'name': forms.TextInput(attrs={'class': "form-control", "readonly": "true"}),
            'money': forms.NumberInput(attrs={'class': "form-control", 'placeholder': '请输入充值金额'}),
        }

