# coding=utf8
from statistic.models import *
import xadmin


class DayStatsAdmin(object):
    """日统计分析"""
    list_display = []
    object_list_template = "statistic/day_stats.html"

    def get_media(self):
        media = super(DayStatsAdmin, self).get_media()
        media.add_css({"screen": ["xadmin/vendor/bootstrap-datepicker/css/datepicker.css"]})
        media.add_css({'screen': ['xadmin/vendor/select2/select2.css']})
        media.add_css({'screen': ['xadmin/vendor/selectize/selectize.css']})
        media.add_css({'screen': ['xadmin/vendor/selectize/selectize.bootstrap3.css']})
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/bootstrap-datepicker.js')])
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/locales/bootstrap-datepicker.zh-CN.js')])
        return media


class MonthStatsAdmin(object):
    """月统计分析"""
    list_display = []
    object_list_template = "statistic/month_stats.html"

    def get_media(self):
        media = super(MonthStatsAdmin, self).get_media()
        media.add_css({"screen": ["xadmin/vendor/bootstrap-datepicker/css/datepicker.css"]})
        media.add_css({'screen': ['xadmin/vendor/select2/select2.css']})
        media.add_css({'screen': ['xadmin/vendor/selectize/selectize.css']})
        media.add_css({'screen': ['xadmin/vendor/selectize/selectize.bootstrap3.css']})
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/bootstrap-datepicker.js')])
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/locales/bootstrap-datepicker.zh-CN.js')])
        return media


class YearStatsAdmin(object):
    """年统计分析"""
    list_display = []
    object_list_template = "statistic/year_stats.html"

    def get_media(self):
        media = super(YearStatsAdmin, self).get_media()
        media.add_css({"screen": ["xadmin/vendor/bootstrap-datepicker/css/datepicker.css"]})
        media.add_css({'screen': ['xadmin/vendor/select2/select2.css']})
        media.add_css({'screen': ['xadmin/vendor/selectize/selectize.css']})
        media.add_css({'screen': ['xadmin/vendor/selectize/selectize.bootstrap3.css']})
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/bootstrap-datepicker.js')])
        media.add_js([self.static('xadmin/vendor/bootstrap-datepicker/js/locales/bootstrap-datepicker.zh-CN.js')])
        return media


xadmin.site.register(DayStats, DayStatsAdmin)
xadmin.site.register(MonthStats, MonthStatsAdmin)
xadmin.site.register(YearStats, YearStatsAdmin)
