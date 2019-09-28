# coding=utf-8
from django.template import Library

register = Library()


# @register.simple_tag
# def gen_role_url(request, rid):
#     params = request.GET.copy()
#     params._mutable = True
#     params['rid'] = rid
#     return params.urlencode()