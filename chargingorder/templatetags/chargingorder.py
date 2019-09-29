# coding=utf-8
from django.template import Library

register = Library()


@register.simple_tag
def is_AC(order):
    if order.charg_pile.pile_type.id == 5 or order.charg_pile.pile_type.id == 6:
        return True
    else:
        return False
    