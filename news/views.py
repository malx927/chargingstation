from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render
from django.views import View
from news.models import Article


class ArticleView(View):
    """文章列表"""
    def get(self, request, *args, **kwargs):
        context = {}
        articles = Article.objects.all()
        current_page = Paginator(articles, 10)

        page = request.GET.get('page')
        try:
            context['articles'] = current_page.page(page)
        except PageNotAnInteger:
            context['articles'] = current_page.page(1)
        except EmptyPage:
            context['articles'] = current_page.page(current_page.num_pages)

        return render(request=request, template_name="weixin/news.html", context=context)


class ArticleDetailView(View):
    """文章详情"""
    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk", None)
        article = Article.objects.filter(id=pk).first()
        context = {
            "article": article
        }
        return render(request=request, template_name="weixin/news_detail.html", context=context)

