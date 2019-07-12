#-*-coding:utf-8-*-
__author__ = 'malxin'


from rest_framework import permissions


class NonPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        return not request.user.is_authenticated()
