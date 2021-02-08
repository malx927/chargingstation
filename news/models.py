from django.db import models
from DjangoUeditor.models import UEditorField


class Article(models.Model):
    """资讯"""
    title = models.CharField(verbose_name="资讯标题", max_length=120)
    title_image = models.ImageField(verbose_name='标题图片', blank=True, null=True)
    author = models.CharField(verbose_name="作者", max_length=32, blank=True, null=True, default='亚电新能源')
    content = UEditorField(verbose_name='资讯内容', width=800, height=400, toolbars='full', imagePath='ueditor/images/', filePath='ueditor/files/', upload_settings={'imageMaxSizing': 1024000}, default='')
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "资讯"
        verbose_name_plural = verbose_name
