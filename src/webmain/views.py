from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.views.generic.list import MultipleObjectMixin
from django.contrib import messages
from django.db.models import Q, Prefetch
from django.shortcuts import render, redirect
from django.urls import reverse

from moderation.models import Collaborations
from webmain.forms import SubscriptionForm
from webmain.models import Faqs, SettingsGlobale,ContactPageInformation, ContactPage, TagsBlogs, AboutPage, HomePage, Seo, Pages, CategorysBlogs, Blogs
from django.http import Http404
import logging

from moderation.models import Advert
from moderation.views import _to_decimal, _to_int
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from moderation.models import CarModel, CarBrand

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
        filtered_blogs = Blogs.objects.all()

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
        if self.request.user.is_authenticated:
            faqs = Faqs.objects.filter(publishet=True, employee=self.request.user.employee)
        else:
            faqs = Faqs.objects.filter(publishet=True,employee=0)
        return faqs

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


class AdvertViewFree(ListView):
    template_name = 'site/website/advertsfree.html'
    context_object_name = 'adverts'
    model = Advert
    paginate_by = 15


    def get_queryset(self):
        g = self.request.GET

        # Базовый queryset:
        qs = Advert.objects.filter(published=True)

        # Фильтрация по текстовому запросу
        q = g.get('q')
        if q:
            text_q = (
                Q(name__icontains=q) |
                Q(subtitle__icontains=q) |
                Q(article__icontains=q) |
                Q(description__icontains=q) |
                Q(brand__icontains=q) |
                Q(model_auto__icontains=q) |
                Q(color__icontains=q)
            )
            qs = qs.filter(text_q)

        # Фильтрация по марке
        brand = g.get('brand')
        if brand:
            qs = qs.filter(brand__iexact=brand)

        # Фильтрация по типу автомобиля (pagetype)
        pagetype = g.get('pagetype')
        if pagetype:
            qs = qs.filter(car_model__pagetype=pagetype)

        # Фильтрация по модели
        model_auto = g.get('model_auto')
        if model_auto:
            qs = qs.filter(model_auto__iexact=model_auto)

        # Фильтрация по топливу
        fuel = g.getlist('fuel')
        if fuel:
            qs = qs.filter(fuel__in=fuel)

        # Фильтрация по году выпуска
        year_min = g.get('year_min')
        year_max = g.get('year_max')
        if year_min:
            qs = qs.filter(year__gte=year_min)
        if year_max:
            qs = qs.filter(year__lte=year_max)

        # Фильтрация по пробегу
        mileage_min = g.get('mileage_min')
        mileage_max = g.get('mileage_max')
        if mileage_min:
            qs = qs.filter(mileage__gte=mileage_min)
        if mileage_max:
            qs = qs.filter(mileage__lte=mileage_max)

        # Фильтрация по мощности
        power_min = g.get('power_min')
        power_max = g.get('power_max')
        if power_min:
            qs = qs.filter(power__gte=power_min)
        if power_max:
            qs = qs.filter(power__lte=power_max)

        # Фильтрация по объему
        engine_volume_min = g.get('engine_volume_min')
        engine_volume_max = g.get('engine_volume_max')
        if engine_volume_min:
            qs = qs.filter(engine_volume__gte=engine_volume_min)
        if engine_volume_max:
            qs = qs.filter(engine_volume__lte=engine_volume_max)

        # Фильтрация по дверям
        doors = g.get('doors')
        if doors:
            qs = qs.filter(doors=doors)

        # Фильтрация по цвету
        color = g.get('color')
        if color:
            qs = qs.filter(color__iexact=color)

        # Фильтрация по наличию изображений
        has_images = g.get('has_images')
        if has_images:
            qs = qs.filter(images__isnull=False)

        # Фильтрация по коробке передач
        transmission = g.getlist('transmission')
        if transmission:
            qs = qs.filter(transmission__in=transmission)
            # Фильтрация по типу привода

        drive = g.getlist('drive')  # Получаем выбранные значения для привода
        if drive:
            qs = qs.filter(drive__in=drive)
        # Фильтрация по цене
        price_min = g.get('price_min')
        price_max = g.get('price_max')
        if price_min:
            qs = qs.filter(price__gte=price_min)
        if price_max:
            qs = qs.filter(price__lte=price_max)

        # Применяем фильтры
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        g = self.request.GET

        # Данные для фильтров из Advert
        filter_adverts_qs = Advert.objects.filter(published=True)

        # Справочные данные для фильтров
        context['brands'] = filter_adverts_qs.exclude(brand__isnull=True).values_list('brand', flat=True).distinct().order_by('brand')

        # Выбираем модели для выбранной марки
        selected_brand = g.get('brand')
        if selected_brand:
            context['models'] = CarModel.objects.filter(brand__name=selected_brand).order_by('name')
        else:
            context['models'] = CarModel.objects.all().order_by('name')

        # Фильтры для других параметров
        context['currencies'] = filter_adverts_qs.exclude(currency__isnull=True).values_list('currency', flat=True).distinct().order_by('currency')
        context['colors'] = filter_adverts_qs.exclude(color__isnull=True).values_list('color', flat=True).distinct().order_by('color')
        context['doors'] = filter_adverts_qs.exclude(doors__isnull=True).values_list('doors', flat=True).distinct().order_by('doors')

        # Список типов автомобилей
        context['pagetype_choices'] = CarModel.PAGE_CHOICE
        context['selected_pagetype'] = g.get('pagetype', '')

        # Фильтры для Топлива и Коробки передач
        context['transmission_choices'] = Advert.TransmissionType.choices
        context['fuel_choices'] = Advert.FuelType.choices
        context['drive_choices'] = Advert.DriveType.choices
        context['selected_transmissions'] = g.getlist('transmission')
        context['selected_fuels'] = g.getlist('fuel')

        context['params'] = g
        return context


class AdvertDetailViewFree(DetailView):
    """Страница новости"""
    model = Advert
    template_name = 'site/website/adverts_detailfree.html'
    context_object_name = 'advert'
    slug_field = "pk"


class AdvertPaymentViewFree(ListView):
    template_name = 'site/website/advertsfree.html'
    context_object_name = 'adverts'
    model = Advert
    paginate_by = 15

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Переадресовываем на страницу с объявлениями, если пользователь уже авторизован
            return redirect('moderation:adverts')
        return super().get(request, *args, **kwargs)


    def get_queryset(self):
        qs = Advert.objects.all().order_by('-created_at')
        g = self.request.GET

        # Поиск
        q = g.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(subtitle__icontains=q) |
                Q(article__icontains=q) |
                Q(description__icontains=q) |
                Q(brand__icontains=q) |
                Q(model_auto__icontains=q) |
                Q(color__icontains=q)
            )

        # Марка/модель
        brand = g.get('brand')
        if brand:
            qs = qs.filter(brand__iexact=brand)

        model_auto = g.get('model_auto')
        if model_auto:
            qs = qs.filter(model_auto__iexact=model_auto)

        # Валюта
        currency = g.get('currency')
        if currency:
            qs = qs.filter(currency__iexact=currency)

        # Цена
        price_min = _to_decimal(g.get('price_min'))
        price_max = _to_decimal(g.get('price_max'))
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)

        # Год
        year_min = _to_int(g.get('year_min'))
        year_max = _to_int(g.get('year_max'))
        if year_min is not None:
            qs = qs.filter(year__gte=year_min)
        if year_max is not None:
            qs = qs.filter(year__lte=year_max)

        # Пробег
        mileage_min = _to_int(g.get('mileage_min'))
        mileage_max = _to_int(g.get('mileage_max'))
        if mileage_min is not None:
            qs = qs.filter(mileage__gte=mileage_min)
        if mileage_max is not None:
            qs = qs.filter(mileage__lte=mileage_max)

        # Мощность
        power_min = _to_int(g.get('power_min'))
        power_max = _to_int(g.get('power_max'))
        if power_min is not None:
            qs = qs.filter(power__gte=power_min)
        if power_max is not None:
            qs = qs.filter(power__lte=power_max)

        # Объем двигателя
        ev_min = _to_decimal(g.get('engine_volume_min'))
        ev_max = _to_decimal(g.get('engine_volume_max'))
        if ev_min is not None:
            qs = qs.filter(engine_volume__gte=ev_min)
        if ev_max is not None:
            qs = qs.filter(engine_volume__lte=ev_max)

        # Двери
        doors = _to_int(g.get('doors'))
        if doors is not None:
            qs = qs.filter(doors=doors)

        # Цвет
        color = g.get('color')
        if color:
            qs = qs.filter(color__icontains=color)

        # Коробка/топливо/привод (множественный выбор)
        transmissions = g.getlist('transmission')
        if transmissions:
            qs = qs.filter(transmission__in=transmissions)

        fuels = g.getlist('fuel')
        if fuels:
            qs = qs.filter(fuel__in=fuels)

        drives = g.getlist('drive')
        if drives:
            qs = qs.filter(drive__in=drives)

        # Есть изображения
        has_images = g.get('has_images')
        if has_images == '1':
            qs = qs.exclude(images__isnull=True).exclude(images=[])

        # Сортировка
        order = g.get('order')
        if order == 'price_asc':
            qs = qs.order_by('price', '-created_at')
        elif order == 'price_desc':
            qs = qs.order_by('-price', '-created_at')
        elif order == 'year_desc':
            qs = qs.order_by('-year', '-created_at')
        elif order == 'year_asc':
            qs = qs.order_by('year', '-created_at')
        elif order == 'mileage_asc':
            qs = qs.order_by('mileage', '-created_at')
        elif order == 'mileage_desc':
            qs = qs.order_by('-mileage', '-created_at')
        else:
            # по умолчанию — свежие
            qs = qs.order_by('-created_at')


        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET

        ctx['brands'] = (Advert.objects.values_list('brand', flat=True)
                         .exclude(brand__isnull=True).exclude(brand__exact='')
                         .distinct().order_by('brand'))
        ctx['models'] = (Advert.objects.values_list('model_auto', flat=True)
                         .exclude(model_auto__isnull=True).exclude(model_auto__exact='')
                         .distinct().order_by('model_auto'))
        ctx['currencies'] = (Advert.objects.values_list('currency', flat=True)
                             .exclude(currency__isnull=True).exclude(currency__exact='')
                             .distinct().order_by('currency'))
        ctx['transmission_choices'] = Advert.TransmissionType.choices
        ctx['fuel_choices'] = Advert.FuelType.choices
        ctx['drive_choices'] = Advert.DriveType.choices

        # чтобы в шаблоне не вызывать getlist(...)
        ctx['selected_transmissions'] = g.getlist('transmission')
        ctx['selected_fuels'] = g.getlist('fuel')
        ctx['selected_drives'] = g.getlist('drive')
        ctx['colors'] = (Advert.objects.values_list('color',flat=True).exclude(currency__isnull=True).exclude(currency__exact='').distinct().order_by('color'))
        ctx['doors'] = (Advert.objects.values_list('doors',flat=True).exclude(currency__isnull=True).exclude(currency__exact='').distinct().order_by('doors'))
        ctx['carmodels'] = (CarModel.objects.values_list('name',flat=True).distinct().order_by('name'))
        ctx['carbrands'] = (CarBrand.objects.values_list('name',flat=True).distinct().order_by('name'))
        carbrands_with_models = CarBrand.objects.prefetch_related(
            Prefetch('models', queryset=CarModel.objects.order_by('name'))
        ).order_by('name')

        # Создаем словарь марка: [модели]
        ctx['carmodels_dict'] = {
            brand.name: list(brand.models.values_list('name', flat=True))
            for brand in carbrands_with_models
        }


        # для остальных полей оставим доступ к params.*
        ctx['params'] = g
        return ctx


class AdvertPaymentDetailViewFree(DetailView):
    """Страница новости"""
    model = Advert
    template_name = 'site/website/adverts_detailfree.html'
    context_object_name = 'advert'
    slug_field = "pk"




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
