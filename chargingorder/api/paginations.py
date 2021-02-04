# -*-coding:utf-8-*-
__author__ = 'malxin'

from rest_framework.pagination import PageNumberPagination


class PagePagination(PageNumberPagination):

    page_size = 20

    # page_query_param = 'page'
    #
    # page_size_query_param = 'rows'
    #
    # max_page_size = None
