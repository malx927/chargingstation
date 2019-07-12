#-*-coding:utf-8-*-
from rest_framework.response import Response

__author__ = 'malxin'

from rest_framework.pagination import PageNumberPagination


class PagePagination(PageNumberPagination):

    page_size = 10
    page_query_param = 'PageNo'
    page_size_query_param = 'PageSize'
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response({
            'ItemSize': self.page.paginator.count,
            'PageCount': self.page.paginator.num_pages,
            'PageNo': self.page.number,
            'StationInfos': data
        })
