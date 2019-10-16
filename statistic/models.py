from django.db import models


class DayStats(models.Model):
    """
    日统计分析
    """
    class Meta:
        verbose_name = "日统计分析"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.Meta.verbose_name


class MonthStats(models.Model):
    """
    月统计分析
    """
    class Meta:
        verbose_name = "月统计分析"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.Meta.verbose_name


class YearStats(models.Model):
    """
    年统计分析
    """
    class Meta:
        verbose_name = "年统计分析"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.Meta.verbose_name


class BigScreen(models.Model):
    """
    数据大屏
    """
    class Meta:
        verbose_name = "数据大屏显示"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.Meta.verbose_name