from django.shortcuts import render
from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.db.models import Q

from moderation.models import Advert


# Create your views here.

def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

def _to_decimal(v):
    try:
        # точка/запятая не важны
        return float(str(v).replace(',', '.'))
    except (TypeError, ValueError):
        return None

class AdvertView(ListView):
    template_name = 'site/useraccount/adverts.html'
    context_object_name = 'adverts'
    model = Advert
    paginate_by = 16

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

        # для остальных полей оставим доступ к params.*
        ctx['params'] = g
        return ctx


class AdvertDetailView(DetailView):
    """Страница новости"""
    model = Advert
    template_name = 'site/useraccount/adverts_detail.html'
    context_object_name = 'advert'
    slug_field = "pk"


