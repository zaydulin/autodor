from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.views.generic.list import MultipleObjectMixin
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse

from moderation.models import Collaborations
from webmain.forms import SubscriptionForm
from webmain.models import Faqs, SettingsGlobale,ContactPageInformation, ContactPage, TagsBlogs, AboutPage, HomePage, Seo, Pages, CategorysBlogs, Blogs
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = 'site/website/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем первую запись HomePage
        homepage = HomePage.objects.first()
        context['homepage'] = homepage  # Сохраняем объект в контексте

        if homepage:
            context['seo_previev'] = homepage.previev
            context['seo_title'] = homepage.title
            context['seo_description'] = homepage.metadescription
            context['seo_propertytitle'] = homepage.propertytitle
            context['seo_propertydescription'] = homepage.propertydescription
        else:
            # Если записи нет, задаем значения по умолчанию
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None

        return context

class AboutView(TemplateView):
    template_name = 'site/website/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем первую запись AboutPage
        aboutpage = AboutPage.objects.first()
        context['aboutpage'] = aboutpage  # Сохраняем объект в контексте

        if aboutpage:
            context['seo_previev'] = aboutpage.previev
            context['seo_title'] = aboutpage.title
            context['seo_description'] = aboutpage.metadescription
            context['seo_propertytitle'] = aboutpage.propertytitle
            context['seo_propertydescription'] = aboutpage.propertydescription
        else:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None
        return context

class ContactView(ListView):
    template_name = 'site/website/contacts.html'
    context_object_name = 'contacts'
    model = ContactPage

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            seo_data = Seo.objects.get(pagetype=3)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.metadescription
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None
        # Добавляем отфильтрованные данные ContactPageInformation по каждой ContactPage
        for contact in context['contacts']:
            contact.phone_default = ContactPageInformation.objects.filter(contact_pages=contact, page_type='phone_default')
            contact.phone = ContactPageInformation.objects.filter(contact_pages=contact, page_type='phone')
            contact.email_default = ContactPageInformation.objects.filter(contact_pages=contact, page_type='email_default')
            contact.email = ContactPageInformation.objects.filter(contact_pages=contact, page_type='email')
            contact.address_default = ContactPageInformation.objects.filter(contact_pages=contact, page_type='address_default')
            contact.address = ContactPageInformation.objects.filter(contact_pages=contact, page_type='address')
            contact.map_default = ContactPageInformation.objects.filter(contact_pages=contact, page_type='map_default')
            contact.map = ContactPageInformation.objects.filter(contact_pages=contact, page_type='map')

        return context


    def post(self, request, *args, **kwargs):
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        phone = request.POST.get('phone')
        message = request.POST.get('message')

        try:
            Collaborations.objects.create(
                name=name,
                email=email,
                subject=subject,
                phone=phone,
                message=message
            )
        except:pass
        return redirect(reverse('webmain:contacts'))


class NearestOnlineTrainingView(LoginRequiredMixin, TemplateView):
    template_name = 'site/website/nearest_training.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.localdate()
        user = self.request.user


        # Получаем блоги, связанные с этими платежами
        related_blogs = Blogs.objects.first()



        # Фильтрация: онлайн, дата >= сегодня, есть стрим
        filtered_blogs = related_blogs.filter(
            pagetype=1,
            data__gte=today,
            stream=True
        ).order_by('data', 'time')


        # Ближайший блог
        blog = filtered_blogs.first()

        context['blog'] = blog
        return context

"""ЧаВо"""
class FaqsView(ListView):
    model = Faqs
    template_name = 'site/website/faqs.html'  # No .html extension
    context_object_name = 'faqs'
    paginate_by = 10

    def get_queryset(self):
        return Faqs.objects.filter(publishet=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            seo_data = Seo.objects.get(pagetype=4)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.metadescription
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None

        return context


"""Страницы"""
class PageDetailView(DetailView):
    """Страница"""
    model = Pages
    template_name = 'site/website/page_detail.html'
    context_object_name = 'page'
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = context['page']
        if page:
            context['pageinformation'] = page.description
            context['seo_previev'] = page.previev
            context['seo_title'] = page.title
            context['seo_description'] = page.metadescription
            context['seo_propertytitle'] = page.propertytitle
            context['seo_propertydescription'] = page.propertydescription
        else:
            context['pageinformation'] = None
        return context


"""Новости"""
class BlogView(ListView):
    model = Blogs
    template_name = 'site/website/blogs.html'
    context_object_name = 'blogs'
    paginate_by = 10

    def get_queryset(self):
        # Основной QuerySet для опубликованных блогов
        queryset = Blogs.objects.filter(publishet=True)

        # Получение параметров фильтрации из GET-запроса
        category = self.request.GET.get('category')
        tag = self.request.GET.get('tag')

        # Фильтрация по категории, если она выбрана
        if category:
            queryset = queryset.filter(category__id=category)

        # Фильтрация по тегу, если он выбран
        if tag:
            queryset = queryset.filter(tags__id=tag)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Передача списка категорий и тегов в контекст
        context['categorys'] = CategorysBlogs.objects.filter(publishet=True)
        context['tags'] = TagsBlogs.objects.filter(publishet=True)

        # Передача текущих фильтров в контекст
        context['selected_category'] = self.request.GET.get('category')
        context['selected_tag'] = self.request.GET.get('tag')

        try:
            seo_data = Seo.objects.get(pagetype=1)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.metadescription
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None

        return context

class BlogDetailView(DetailView):
    """Страница новости"""
    model = Blogs
    template_name = 'site/website/blog_detail.html'
    context_object_name = 'blog'
    slug_field = "slug"

    def get_queryset(self):
        return Blogs.objects.filter(publishet=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorys'] = CategorysBlogs.objects.all().filter(publishet=True)
        context['tags'] = TagsBlogs.objects.all().filter(publishet=True)
        blog = context['blog']
        if blog:
            context['pageinformation'] = blog.description
            context['seo_previev'] = blog.previev
            context['seo_title'] = blog.title
            context['seo_description'] = blog.metadescription
            context['seo_propertytitle'] = blog.propertytitle
            context['seo_propertydescription'] = blog.propertydescription
        else:
            context['pageinformation'] = None
        return context


"""Подписка"""
def subscribe(request):
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Спасибо за подписку!')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        else:
            messages.error(request, f'Вы уже подписаны на рассылку!')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


"""Поиск"""
class MultiModelSearchView(ListView):
    template_name = 'site/website/search.html'
    context_object_name = 'results'
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        filter_type = self.request.GET.get('filter', 'all')
        current_domain = self.request.get_host()  # Получаем текущий домен

        if not query:
            return []

        results = []

        if filter_type in ('', 'all', 'blogs'):
            blog_results = Blogs.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
            for blog in blog_results:
                blog.type = 'blog'  # Добавляем атрибут типа
            results.extend(blog_results)

        if filter_type == 'pages' or filter_type == '' or filter_type == 'all':
            page_results = Pages.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
            for page in page_results:
                page.type = 'page'  # Добавляем атрибут типа
            results.extend(page_results)

        return results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['filter'] = self.request.GET.get('filter', '')

        try:
            seo_data = Seo.objects.get(pagetype=2)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.metadescription
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None

        return context
