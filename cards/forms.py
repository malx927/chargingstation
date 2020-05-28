# -*- coding:utf-8 -*-
from cards.models import CardRecharge
from django import forms


class CardRechargeForm(forms.ModelForm):
    """充值卡充值"""
    def __init__(self, *args, **kwargs):
        super(CardRechargeForm, self).__init__(*args, **kwargs)
        # self.fields['user'].required = False

    class Meta:
        model = CardRecharge
        fields = ["card", "money"]

        widgets = {
            'card': forms.Select(attrs={'class': "form-control", "readonly": "true"}),
            # 'user': forms.Select(attrs={'class': "form-control", "readonly": "true"}),
            'money': forms.NumberInput(attrs={'class': "form-control", 'placeholder': '请输入充值金额'}),
        }

