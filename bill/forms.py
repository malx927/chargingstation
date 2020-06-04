# -*- coding:utf-8 -*-
from bill.models import InvoiceTitle
from cards.models import CardRecharge
from django import forms


class InvoiceTitleForm(forms.ModelForm):
    """发票抬头"""
    def __init__(self, *args, **kwargs):
        super(InvoiceTitleForm, self).__init__(*args, **kwargs)

    class Meta:
        model = InvoiceTitle
        fields = ["title", "category", "tax_number", "address", "telephone", "bank_account", "email", "invoice_style"]

        # widgets = {
        #     'card': forms.TextInput(attrs={'class': "form-control", "readonly": "true"}),
        #     'money': forms.NumberInput(attrs={'class': "form-control", 'placeholder': '请输入充值金额'}),
        # }

