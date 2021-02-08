# coding=utf-8
import logging

from django.db.models import Q
from django.urls import reverse
import xadmin
from news.models import Article
from xadmin.layout import Fieldset, Main, Side, Row, AppendedText


class ArticleAdmin(object):
    list_display = ['title', 'author', 'add_time']
    search_fields = ['title']
    list_filter = ['add_time']
    list_per_page = 50
    model_icon = 'fa fa-file-text'
    show_all_rel_details = False
    relfield_style = 'fk_ajax'
    style_fields = {"content": "ueditor"}


xadmin.site.register(Article, ArticleAdmin)
