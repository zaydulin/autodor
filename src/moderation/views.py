import base64
import io
import json
import os
import traceback
from audioop import reverse
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models.functions import TruncDate
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import NoReverseMatch
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views import View
from moderation.tasks import start_call_task, end_call_task
from django.contrib.auth.mixins import UserPassesTestMixin

from django.contrib.auth.decorators import login_required
from django.db import models, transaction, IntegrityError
from django.http import JsonResponse, HttpResponse, HttpResponseServerError, FileResponse, HttpResponseBadRequest, \
    HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.db.models import Q, Prefetch, Count
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import PathForm, AdvertAplicationGalleryForm
from .models import AdvertAplication, ChatMessage, CallSession, AdvertDocument, AdvertExpense, AdvertApplicationImage, \
    CarModel, CarBrand, AdvertAplicationGallery, ExpenseMask, AdvertAplicationGalleryGroup, CartVod, WalletDriver
from moderation.models import Advert, AdvertAplication,Path,PathResponsibility, Withdrawal
from webmain.models import Faqs, Seo
from useraccount.models import Profile

from webmain.models import SettingsGlobale
from django.db.models import Sum
from django.contrib import messages


class CustomHtmxMixin:
    def get_template_names(self):
        is_htmx = bool(self.request.META.get('HTTP_HX_REQUEST'))
        if is_htmx:
            return [self.template_name]
        else:
            return ['include_block.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_htmx'] = self.template_name

        # Получаем SEO данные из View и передаем их для блоков
        seo_context = self.get_seo_context()
        context.update(seo_context)

        return context

    def get_seo_context(self):
        """
        Переопределите этот метод в дочерних классах
        чтобы вернуть SEO данные для этой страницы
        """
        return {
            'block_title': 'Заголовок по умолчанию',
            'block_description': 'Описание по умолчанию',
            'block_propertytitle': 'Property Title по умолчанию',
            'block_propertydescription': 'Property Description по умолчанию',
            'block_propertyimage': '',
            'block_head': ''
        }



def car_model_list(request):
    # Получаем все модели автомобилей
    car_models = CarModel.objects.all()

    # Передаем модели в шаблон
    return render(request, 'car_model_list.html', {'car_models': car_models})
def change_car_model_type(request, model_id):
    # Получаем модель автомобиля по ID
    car_model = get_object_or_404(CarModel, id=model_id)

    if request.method == 'POST':
        # Получаем новый тип модели из POST-запроса
        new_type = request.POST.get('pagetype')

        if not new_type:
            return JsonResponse({'success': False, 'message': 'Тип не указан'})

        try:
            # Преобразуем в целое число
            new_type = int(new_type)

            # Проверяем, что новый тип модели существует в Choices
            if new_type not in [choice[0] for choice in CarModel.PAGE_CHOICE]:
                return JsonResponse({'success': False, 'message': 'Некорректный тип модели'})

            # Изменяем тип модели
            car_model.pagetype = new_type
            car_model.save()

            return JsonResponse({
                'success': True,
                'message': f"Тип модели {car_model.name} успешно изменен на {car_model.get_pagetype_display()}"
            })
        except ValueError as e:
            # Логируем ошибку для отладки
            return JsonResponse({'success': False, 'message': f'Неверный формат типа модели: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Неверный метод запроса'})


class AdvertStatisticsView(UserPassesTestMixin, CustomHtmxMixin, TemplateView):
    template_name = 'advert_statistics.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ---- Приложения и пагинация ----
        applications = AdvertAplication.objects.all().order_by('created_at')
        paginator = Paginator(applications, 5)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # ---- Суммы расходов и выводов (агрегируем по всем приложениям) ----
        total_expenses_all = 0
        total_withdrawals_all = 0
        for application in applications:
            total_expenses = application.expenses.aggregate(Sum('amount'))['amount__sum'] or 0
            total_withdrawals = Withdrawal.objects.filter(application=application).aggregate(Sum('amount'))['amount__sum'] or 0
            total_expenses_all += total_expenses
            total_withdrawals_all += total_withdrawals

        # ---- Статистика по датам для графика ----
        stats_qs = (
            AdvertAplication.objects
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                price_sum=Sum('price'),
                expenses_sum=Sum('expenses__amount'),
                withdrawals_sum=Sum('withdrawal__amount'),
            )
            .order_by('date')
        )

        chart_labels = [s['date'].strftime('%d.%m') for s in stats_qs if s['date']]
        chart_prices = [float(s['price_sum'] or 0) for s in stats_qs]
        chart_expenses = [float(s['expenses_sum'] or 0) for s in stats_qs]
        chart_withdrawals = [float(s['withdrawals_sum'] or 0) for s in stats_qs]

        # ---- TOP-9 CarBrand из AdvertAplication -> advert_id -> Advert.car_brand ----
        top_car_brands = []  # список словарей {'brand': CarBrand, 'count': int}

        # Собираем уникальные advert_id из AdvertAplication
        advert_ids_qs = AdvertAplication.objects.values_list('advert_id', flat=True).distinct()
        advert_ids = [str(x) for x in advert_ids_qs if x not in (None, "", "None")]

        adverts_qs = Advert.objects.none()
        try:
            if advert_ids:
                # 1) Попытка по числовым id (advert_id как числа → pk Advert)
                numeric_ids = [int(a) for a in advert_ids if a.isdigit()]
                if numeric_ids:
                    adverts_qs = Advert.objects.filter(id__in=numeric_ids, car_brand__isnull=False)

                # 2) Если пусто и в модели Advert есть поле advert_id — пробуем по нему
                if not adverts_qs.exists() and hasattr(Advert, 'advert_id'):
                    adverts_qs = Advert.objects.filter(advert_id__in=advert_ids, car_brand__isnull=False)

                # 3) Если всё ещё пусто — пробуем pk__in (на случай UUID в виде строки)
                if not adverts_qs.exists():
                    try:
                        adverts_qs = Advert.objects.filter(pk__in=advert_ids, car_brand__isnull=False)
                    except Exception:
                        adverts_qs = adverts_qs.none()

            # Агрегируем по car_brand
            if adverts_qs.exists():
                brand_counts = (
                    adverts_qs
                    .values('car_brand')
                    .annotate(cnt=Count('id'))
                    .order_by('-cnt')[:9]
                )
                brand_ids_ordered = [bc['car_brand'] for bc in brand_counts if bc['car_brand'] is not None]
                brands = CarBrand.objects.filter(id__in=brand_ids_ordered)
                brand_map = {b.id: b for b in brands}
                for bc in brand_counts:
                    bid = bc.get('car_brand')
                    if bid and bid in brand_map:
                        top_car_brands.append({'brand': brand_map[bid], 'count': bc.get('cnt', 0)})
        except Exception:
            traceback.print_exc()

        # Заполняем ровно 9 контекстных переменных top_car_brand_1 ... top_car_brand_9
        for idx in range(9):
            key = f"top_car_brand_{idx+1}"
            if idx < len(top_car_brands):
                context[key] = top_car_brands[idx]
            else:
                context[key] = None

        # Дополнительно список и флаг
        context['top_car_brands_list'] = top_car_brands
        context['has_top_car_brands'] = bool(top_car_brands)

        # ---- Обновляем основной контекст ----
        context.update({
            'page_obj': page_obj,
            'total_expenses_all': total_expenses_all,
            'total_withdrawals_all': total_withdrawals_all,
            'chart_labels': chart_labels,
            'chart_prices': chart_prices,
            'chart_expenses': chart_expenses,
            'chart_withdrawals': chart_withdrawals,
        })

        return context


@csrf_exempt
def add_gallery_group(request):
    if request.method == "POST" and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            app = AdvertAplication.objects.get(id=data.get("application_id"))
            group = AdvertAplicationGalleryGroup.objects.create(
                application=app,
                title=data.get("title"),
                description=data.get("description", "")
            )
            return JsonResponse({"success": True, "id": group.id})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Неверный запрос"})



@login_required
@require_POST
def add_gallery_group_with_items(request, pk):
    application = get_object_or_404(AdvertAplication, pk=pk)

    title = request.POST.get("title")
    description = request.POST.get("description", "")
    files = request.FILES.getlist("files[]")
    report_description = request.POST.get("report_description", "")
    report_type = request.POST.get("report_type")

    if not title or not files:
        if request.headers.get("HX-Request") == "true":
            return HttpResponse("Название и файлы обязательны", status=400)
        return redirect(request.META.get("HTTP_REFERER", "/"))

    # 1. Создаём группу
    group = AdvertAplicationGalleryGroup.objects.create(
        application=application,
        title=title,
        description=description,
        position=application.gallery_groups.count() + 1,
    )

    # 2. Создаём файлы
    for f in files:
        filename = f.name.lower()
        if report_type == "ticket":
            pagetype = 2
        elif report_type == "receipt":
            pagetype = 3
        else:
            if filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                pagetype = 0
            elif filename.endswith((".mp4", ".mov", ".webm", ".mkv")):
                pagetype = 1
            else:
                pagetype = 0

        AdvertAplicationGallery.objects.create(
            application=application,
            group=group,
            file=f,
            description=report_description,
            uploaded_by=request.user,
            pagetype=pagetype,
        )

    # 3. Если htmx — возвращаем фрагменты и скрипт для отложенного обновления activity-list
    if request.headers.get("HX-Request") == "true":
        # HTML новой группы (тот, который вставляется в DOM сразу)
        gallery_html = render_to_string(
            "moderation/partials/gallery_group_item.html",
            {"group": group, "application": application},
            request=request,
        )

        # Сразу формируем HTML для activity-list (весь innerHTML контейнера, т.е. только <li> или полный HTML в зависимости от шаблона)
        # Рекомендуется, чтобы activity_list-template возвращал именно содержимое <ul> (только <li>...), а контейнер <ul id="activity-list"> был в основном шаблоне.
        activity_inner_html = render_to_string(
            "moderation/partials/activity-list.html",
            {"application": application},
            request=request,
        )

        # Экранируем HTML для безопасной вставки в JS-строку
        activity_inner_html_js = json.dumps(activity_inner_html)

        # Скрипт: через 2000ms заменит innerHTML контейнера #activity-list на подготовленный HTML
        # Используем .innerHTML напрямую — это быстрее и надёжнее, чем дополнительный HTMX GET,
        # и не требует никаких дополнительных URL/маршрутов.
        activity_refresh_script = (
            "<script>"
            "setTimeout(function(){"
            f"  try {{"
            f"    var el = document.getElementById('activity-list');"
            f"    if(el) el.innerHTML = {activity_inner_html_js};"
            f"  }} catch(e) {{ console.error('activity-list update error', e); }};"
            "}, 2000);"
            "</script>"
        )

        # (Опционально) OOB — можно оставить или убрать; если хочешь только отложенное обновление, убери activity_oob_html.
        activity_oob_html = f'<template hx-swap-oob="true" hx-target="#activity-list">{activity_inner_html}</template>'

        # Возвращаем HTML новой группы + (опционально) OOB + скрипт для отложенного обновления
        return HttpResponse(gallery_html + activity_oob_html + activity_refresh_script)

    # fallback для обычного запроса
    return redirect(request.META.get("HTTP_REFERER", "/"))





@login_required
@require_http_methods(["GET", "POST"])
def driver_wallet_view(request, application_id, driver_id):
    """View для работы с кошельком водителя"""
    try:
        application = get_object_or_404(AdvertAplication, id=application_id)
        driver = get_object_or_404(Profile, id=driver_id)

        # Проверяем права доступа
        if not (request.user in application.user_menager.all() or request.user.employee == 4):
            return JsonResponse({'error': 'Нет прав доступа'}, status=403)

        # Получаем или создаем кошелек
        cart_vod, created = CartVod.objects.get_or_create(
            application=application,
            voditel=driver,
            defaults={'summa': 0}
        )

        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'driver_name': f"{driver.first_name} {driver.last_name}",
                'current_amount': float(cart_vod.summa),
                'formatted_amount': f"{cart_vod.summa:.2f} руб.",
                'application_id': application.id,
                'driver_id': driver.id
            })

        elif request.method == 'POST':
            new_amount = request.POST.get('amount')
            if not new_amount:
                return JsonResponse({'error': 'Сумма не указана'}, status=400)

            try:
                new_amount = Decimal(new_amount)
                if new_amount < 0:
                    return JsonResponse({'error': 'Сумма не может быть отрицательной'}, status=400)

                cart_vod.summa = new_amount
                cart_vod.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Сумма успешно обновлена',
                    'new_amount': float(cart_vod.summa),
                    'formatted_amount': f"{cart_vod.summa:.2f} руб."
                })

            except (ValueError, InvalidOperation) as e:
                return JsonResponse({'error': 'Неверный формат суммы'}, status=400)

    except Exception as e:
        print(f"Error in driver_wallet_view: {str(e)}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

class PathDeleteView(View):
    """
    Удаление этапа через htmx.
    """

    def post(self, request, pk):
        path = get_object_or_404(Path, pk=pk)
        application = path.aplication
        path.delete()

        # После удаления тоже возвращаем обновлённый список
        paths = Path.objects.filter(aplication=application).select_related("responsible").order_by("id")
        html = render_to_string(
            "moderation/partials/pathr.html",
            {"paths": paths},
            request=request,
        )
        return HttpResponse(html)


class PathSaveView(View):
    def post(self, request, application_id):
        application = get_object_or_404(AdvertAplication, id=application_id)

        stage_id = request.POST.get("stage_id")
        name = request.POST.get("name") or ""
        description = request.POST.get("description") or ""
        participant_id = request.POST.get("participant_id")
        lat_raw = request.POST.get("lat")
        lng_raw = request.POST.get("lng")

        errors = {}

        if not name:
            errors["name"] = "Название этапа обязательно"

        if not participant_id:
            errors["participant_id"] = "Участник обязателен"

        def parse_float(value, field_name):
            if not value:
                return None
            try:
                return float(value.replace(",", "."))
            except Exception:
                errors[field_name] = "Некорректное значение"
                return None

        latitude = parse_float(lat_raw, "lat")
        longitude = parse_float(lng_raw, "lng")

        if errors:
            if request.headers.get("HX-Request") == "true":
                return HttpResponse(
                    "; ".join(f"{k}: {v}" for k, v in errors.items()),
                    status=400,
                )
            return JsonResponse({"success": False, "errors": errors}, status=400)

        responsible = get_object_or_404(Profile, pk=participant_id)

        if stage_id:
            path = get_object_or_404(Path, pk=stage_id, aplication=application)
        else:
            path = Path(aplication=application)
            path.request = application.order_number or str(application.id)

        path.name = name
        path.description = description
        path.responsible = responsible
        if latitude is not None:
            path.latitude = latitude
        if longitude is not None:
            path.longitude = longitude

        path.save()

        # Перерисовываем список этапов
        paths = Path.objects.filter(aplication=application).select_related("responsible").order_by("id")
        html = render_to_string(
            "moderation/partials/pathr.html",
            {"paths": paths},          # 👈 ВАЖНО: paths, как в шаблоне
            request=request,
        )

        return HttpResponse(html)


# moderation/views.py
STATUS_DISPLAY = {
    'принял': 'Принял',
    'закончил': 'Закончил',
}

def responsibility_form(request, pk=None):
    instance = get_object_or_404(PathResponsibility, pk=pk) if pk else None

    def resolve_application_id():
        if instance and instance.path_choice_id:
            return instance.path_choice.aplication_id
        return request.GET.get('application_id') or request.POST.get('application_id')

    if request.method == "POST":
        form = PathResponsibilityForm(request.POST, instance=instance, application_id=resolve_application_id())
        if form.is_valid():
            obj = form.save()
            return JsonResponse({
                "success": True,
                "responsibility": {
                    "id": obj.id,
                    "additional": obj.additional,
                    # было: obj.get_status_display()
                    "status": STATUS_DISPLAY.get(obj.status, obj.status),
                    "responsible": str(obj.responsible),
                }
            })
        html = render_to_string("moderation/includes/responsibility_form.html", {"form": form}, request=request)
        return JsonResponse({"success": False, "html": html})

    form = PathResponsibilityForm(instance=instance, application_id=resolve_application_id())
    html = render_to_string("moderation/includes/responsibility_form.html", {"form": form}, request=request)
    return JsonResponse({"success": True, "html": html})


class AdvertAplicationListView(CustomHtmxMixin, LoginRequiredMixin, ListView):
    model = AdvertAplication
    template_name = "site/useraccount/advertaplication.html"
    context_object_name = "advertaplications"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        advert_aplications = (
            AdvertAplication.objects.using("default")
            .filter(
                models.Q(user=user)
                | models.Q(user_menager=user)
                | models.Q(user_drivers=user)
            )
            .prefetch_related("user", "user_menager", "user_drivers")
            .distinct()
            .order_by("-created_at")
        )

        # Получаем данные по `advert_id` из другой базы данных
        for advertaplication in advert_aplications:
            try:
                advert = Advert.objects.using('adverts').get(id=advertaplication.advert_id)
                advertaplication.advert = advert  # Привязываем найденный объект к текущему
            except Advert.DoesNotExist:
                advertaplication.advert = None

        return advert_aplications



def expense_masks_json(request):
    """Вернёт все маски в JSON для автодополнения"""
    q = request.GET.get("q", "")
    masks = ExpenseMask.objects.all()
    if q:
        masks = masks.filter(name__icontains=q)
    return JsonResponse({"results": [m.name for m in masks[:20]]})




class AdvertAplicationDetailView(CustomHtmxMixin, LoginRequiredMixin, DetailView):
    model = AdvertAplication
    template_name = "site/useraccount/advertaplication-detail.html"
    context_object_name = "application"

    def get_queryset(self):
        user = self.request.user

        return (
            AdvertAplication.objects.using("default")
            .filter(
                Q(user=user)
                | Q(user_menager=user)
                | Q(user_drivers=user)
            )
            .prefetch_related("user", "user_menager", "user_drivers")
            .distinct()
        )

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        # Если это HTMX и ещё нет флага в сессии
        if request.headers.get("HX-Request") == "true" and not request.session.get("htmx_detail_reload", False):
            request.session["htmx_detail_reload"] = True
            # Возвращаем скрипт для перезагрузки
            from django.http import HttpResponse
            return HttpResponse(
                '<script>window.location.reload();</script>'
            )

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application: AdvertAplication = self.object

        # --- Объявление из внешней БД ---
        advert = application.get_advert()  # может вернуть None
        context["application"] = application
        context["advert"] = advert

        # --- Кошельки водителей по заявке ---
        wallets = (
            WalletDriver.objects.filter(aplication=application)
            .select_related("responsible")
        )
        wallets_by_driver = {w.responsible_id: w for w in wallets}
        context["wallets_by_driver"] = wallets_by_driver

        # --- Расходы ---
        expenses = application.expenses.all()
        context["expenses"] = expenses
        total_expenses = sum(exp.amount for exp in expenses) if expenses else Decimal("0")
        context["total_expenses"] = total_expenses

        # --- Общая стоимость ---
        if advert and getattr(advert, "price", None) is not None:
            total_price = advert.price
        else:
            total_price = application.price or Decimal("0")

        context["total_price"] = total_price
        context["total_ost"] = total_price - total_expenses

        # Обновляем цену заявки остатком
        application.price = context["total_ost"]
        application.save(update_fields=["price"])

        # --- Пользователи заявки (кроме текущего) ---
        users_list = []
        users_list.extend(application.user.all())
        users_list.extend(application.user_menager.all())
        users_list.extend(application.user_drivers.all())

        context["users"] = [
            u for u in users_list if u is not None and u != self.request.user
        ]

        # "основной" пользователь заявки (первый в списке user)
        main_user = application.user.first()

        # --- Сообщения по заявке ---
        messages_qs = (
            ChatMessage.objects.filter(applications=application)
            .filter(
                Q(author=main_user)
                | Q(author__in=application.user_menager.all())
                | Q(author__in=application.user_drivers.all())
            )
            .order_by("date")
        )
        context["messages"] = messages_qs

        # --- Звонки / документы / маски ---
        context["calls"] = CallSession.objects.filter(application=application)
        context["documents"] = application.documents.all().order_by("-created_at")
        context["expense_masks"] = ExpenseMask.objects.all()

        # --- Списки менеджеров и водителей (для форм) ---
        context["all_managers"] = Profile.objects.filter(type=0, employee=2)
        context["all_drivers"] = Profile.objects.filter(type=0, employee=1)

        # --- Маршруты (этапы) ---
        paths = Path.objects.filter(aplication=application).select_related("responsible")
        context["paths"] = paths
        context["path_responsibilitys"] = PathResponsibility.objects.filter(
            path_choice__in=paths
        )

        # 🔹 Этап "Принял" (status = 1)
        current_path = (
            paths.filter(status=1)
            .select_related("responsible")
            .first()
        )
        context["current_path"] = current_path

        # 🔹 Текущий водитель и его кошелёк
        current_driver = None
        current_driver_wallet = None

        if current_path is not None and current_path.responsible:
            current_driver = current_path.responsible  # Profile(AbstractUser)

        if current_driver is not None:
            current_driver_wallet = wallets_by_driver.get(current_driver.id)

        context["current_driver"] = current_driver
        context["current_driver_wallet"] = current_driver_wallet

        # 🔹 Итоговые координаты для машинки:
        #   1) пытаемся взять живые координаты из Profile
        #   2) если их нет, берём координаты этапа (Path)
        driver_lat = None
        driver_lng = None

        if current_driver is not None and current_driver.latitude is not None and current_driver.longitude is not None:
            driver_lat = current_driver.latitude
            driver_lng = current_driver.longitude
        elif current_path is not None and current_path.latitude is not None and current_path.longitude is not None:
            driver_lat = current_path.latitude
            driver_lng = current_path.longitude

        context["current_driver_lat"] = driver_lat
        context["current_driver_lng"] = driver_lng

        return context



User = get_user_model()

class WalletDriverView(View):
    def get(self, request, application_id, driver_id):
        application = get_object_or_404(AdvertAplication, id=application_id)
        driver = get_object_or_404(User, id=driver_id)

        wallet, _ = WalletDriver.objects.get_or_create(
            aplication=application,
            responsible=driver,
            defaults={"balance": 0, "spent": 0},
        )

        modal_html = render_to_string(
            "moderation/partials/wallet_driver_modal.html",
            {
                "application": application,
                "driver": driver,
                "wallet": wallet,
            },
            request=request,
        )
        return HttpResponse(modal_html)

    def post(self, request, application_id, driver_id):
        application = get_object_or_404(AdvertAplication, id=application_id)
        driver = get_object_or_404(User, id=driver_id)

        wallet, _ = WalletDriver.objects.get_or_create(
            aplication=application,
            responsible=driver,
            defaults={"balance": 0, "spent": 0},
        )

        balance_raw = request.POST.get("balance")
        spent_raw = request.POST.get("spent")

        def parse_decimal(raw, default="0"):
            if raw in (None, ""):
                raw = default
            return Decimal(str(raw).replace(",", "."))

        wallet.balance = parse_decimal(balance_raw)
        wallet.spent = parse_decimal(spent_raw)
        wallet.save()

        # 1) снова рендерим модалку (чтобы там были актуальные значения)
        modal_html = render_to_string(
            "moderation/partials/wallet_driver_modal.html",
            {
                "application": application,
                "driver": driver,
                "wallet": wallet,
            },
            request=request,
        )

        # 2) обновляем блок со всеми водителями
        wallets = WalletDriver.objects.filter(
            aplication=application
        ).select_related("responsible")
        wallets_by_driver = {w.responsible_id: w for w in wallets}

        drivers_html = render_to_string(
            "moderation/partials/driver_wallets_block.html",
            {
                "application": application,
                "wallets_by_driver": wallets_by_driver,
            },
            request=request,
        )

        full_html = (
            modal_html +
            f'<div id="driver-wallets-block" hx-swap-oob="innerHTML">{drivers_html}</div>'
        )

        return HttpResponse(full_html)



class PathChangeStatusView(View):
    """
    Смена статуса этапа (Path) через htmx.
    """

    def post(self, request, pk):
        path = get_object_or_404(Path, pk=pk)
        application = path.aplication  # поле aplication в модели Path

        new_status = request.POST.get("status")

        # Допустимые статусы из choices
        allowed_values = {str(choice[0]) for choice in Path.STATUS_CHOICES}

        if new_status not in allowed_values:
            if request.headers.get("HX-Request") == "true":
                return HttpResponse("Некорректный статус", status=400)
            return JsonResponse({"success": False, "error": "Некорректный статус"}, status=400)

        path.status = int(new_status)
        path.save()

        # Перерисовываем список этапов для этой заявки
        paths = Path.objects.filter(aplication=application).select_related("responsible").order_by("id")

        html = render_to_string(
            "moderation/partials/pathr.html",
            {"paths": paths},
            request=request,
        )
        return HttpResponse(html)

@csrf_exempt
@require_http_methods(["POST"])
def create_path(request):
    try:
        data = json.loads(request.body)
        form = PathForm(data)

        if form.is_valid():
            path = form.save()
            return JsonResponse({
                'success': True,
                'path': {
                    'id': path.id,
                    'name': path.name,
                    'description': path.description,
                    'longitude': path.longitude,
                    'latitude': path.latitude
                }
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def update_path(request, path_id):
    try:
        path = get_object_or_404(Path, id=path_id)
        data = json.loads(request.body)
        form = PathForm(data, instance=path)

        if form.is_valid():
            path = form.save()
            return JsonResponse({
                'success': True,
                'path': {
                    'id': path.id,
                    'name': path.name,
                    'description': path.description
                }
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_path(request, path_id):
    try:
        path = get_object_or_404(Path, id=path_id)
        path.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def create_responsibility(request):
    try:
        # Получаем данные из POST
        application_id = request.POST.get("application_id")
        path_choice_id = request.POST.get("path_choice_id")
        status = request.POST.get("status")
        responsible_id = request.POST.get("responsible_id")
        additional = request.POST.get("additional", "")

        # Проверяем объекты
        application = get_object_or_404(AdvertAplication, id=application_id)
        path_choice = get_object_or_404(Path, id=path_choice_id)
        responsible = get_object_or_404(Profile, id=responsible_id)

        # Создаём PathResponsibility
        PathResponsibility.objects.create(
            path_choice=path_choice,
            status=status,
            responsible=responsible,
            additional=additional
        )

        # Получаем все PathResponsibility для этой заявки
        path_responsibilitys = PathResponsibility.objects.filter(
            path_choice__aplication=application
        ).order_by("id")  # или "created_at" если есть поле

        # Вернуть HTML для htmx прямо здесь
        return render(
            request,
            "moderation/partials/path_responsibility_item.html",  # используем один шаблон
            {"path_responsibilitys": path_responsibilitys}
        )

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



@require_http_methods(["POST"])
def update_responsibility(request):
    try:
        responsibility_id = request.POST.get("responsibility_id")
        path_choice_id = request.POST.get("path_choice_id")
        status = request.POST.get("status")
        responsible_id = request.POST.get("responsible_id")
        additional = request.POST.get("additional", "")

        # Если responsibility_id передан — обновляем, иначе создаём новую запись
        if responsibility_id:
            responsibility = get_object_or_404(PathResponsibility, id=responsibility_id)
        else:
            responsibility = PathResponsibility()

        if path_choice_id:
            responsibility.path_choice = get_object_or_404(Path, id=path_choice_id)
        if responsible_id:
            responsibility.responsible = get_object_or_404(Profile, id=responsible_id)

        responsibility.status = status
        responsibility.additional = additional
        responsibility.save()

        application = responsibility.path_choice.aplication

        # Берём все PathResponsibility для данного приложения
        path_responsibilitys = PathResponsibility.objects.filter(
            path_choice__aplication=application
        ).order_by("id")

        # Рендерим шаблон с обновлённым списком
        return render(
            request,
            "moderation/partials/path_responsibility_item.html",
            {"path_responsibilitys": path_responsibilitys, "application": application}
        )

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



@require_http_methods(["POST"])
def delete_responsibility(request, responsibility_id):
    try:
        responsibility = get_object_or_404(PathResponsibility, id=responsibility_id)
        application = responsibility.path_choice.aplication
        responsibility.delete()

        # Вернуть обновлённый список
        path_responsibilitys = PathResponsibility.objects.filter(
            path_choice__aplication=application
        ).order_by("id")

        return render(
            request,
            "moderation/partials/path_responsibility_item.html",
            {"path_responsibilitys": path_responsibilitys}
        )

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def document_editor(request,document_id):
    document = get_object_or_404(AdvertDocument, id=document_id)

    pdf_bytes = document.file.read()  # или другой способ получения PDF
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    return render(request, 'pdf_form.html', {
        'document': document,
        'pdf_base64': pdf_base64,
    })


@require_POST
def save_document(request, pk):
    document = get_object_or_404(AdvertDocument, pk=pk)
    uploaded_file = request.FILES.get('file_bytes')
    if not uploaded_file:
        return JsonResponse({'error': 'No file received'}, status=400)

    # Сохраняем файл
    document.file.save('modified.pdf', uploaded_file)
    document.save()
    return JsonResponse({'status': 'success'})

class UpdateApplicationView(View):
    def post(self, request, application_id):
        application = get_object_or_404(AdvertAplication, id=application_id)

        # Обработка полей, статус, менеджеры, водители, деньги
        status = request.POST.get("status")
        managers_ids = request.POST.getlist("user_menager")
        drivers_ids = request.POST.getlist("user_drivers")

        # Десериализация decimal полей с проверкой
        def parse_decimal(raw_value):
            if not raw_value:
                return None
            try:
                return Decimal(raw_value.replace(",", "."))
            except:
                return None

        application.status = status or application.status
        application.user_menager.set(Profile.objects.filter(id__in=managers_ids) if managers_ids else [])
        application.user_drivers.set(Profile.objects.filter(id__in=drivers_ids) if drivers_ids else [])
        application.delevery_price = parse_decimal(request.POST.get("delevery_price")) or application.delevery_price
        application.balance = parse_decimal(request.POST.get("balance")) or application.balance
        application.current_balance = parse_decimal(request.POST.get("current_balance")) or application.current_balance
        application.expenses_total = parse_decimal(request.POST.get("expenses_total")) or application.expenses_total

        application.save()

        if request.headers.get("HX-Request") == "true":
            # HTML sidebar и баланса
            finance_html = render_to_string(
                "moderation/partials/application_sidebar.html",
                {"application": application},
                request=request,
            )
            set_balance_html = render_to_string(
                "moderation/partials/set-balanse.html",
                {"application": application},
                request=request,
            )

            # HTML activity-list (только <li>)
            activity_inner_html = render_to_string(
                "moderation/partials/activity-list.html",
                {"application": application},
                request=request,
            )
            activity_inner_html_js = json.dumps(activity_inner_html)

            # Скрипт: через 2 секунды обновляет #activity-list
            activity_refresh_script = (
                "<script>"
                "setTimeout(function(){"
                f"  try {{"
                f"    var el = document.getElementById('activity-list');"
                f"    if(el) el.innerHTML = {activity_inner_html_js};"
                f"  }} catch(e) {{ console.error('activity-list update error', e); }};"
                "}, 2000);"
                "</script>"
            )

            # Формируем полный HTML ответа
            full_html = (
                f'<div id="application-finance">{finance_html}</div>'
                f'<div id="set-balanse" class="d-flex justify-content-between" hx-swap-oob="outerHTML">'
                f'{set_balance_html}</div>'
                + activity_refresh_script
            )

            return HttpResponse(full_html)

        return JsonResponse({
            "success": True,
            "message": "Заявка успешно обновлена",
            "application_id": str(application.id),
        })


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
from django.db.models import Q
from django.views.generic import ListView
from .models import Advert, CarModel


class AdvertView(CustomHtmxMixin, ListView):
    template_name = 'site/useraccount/adverts.html'
    context_object_name = 'adverts'
    model = Advert
    paginate_by = 15

    def get_queryset(self):
        g = self.request.GET

        # Базовый queryset
        qs = Advert.objects.filter(published=True)

        # ДЕФОЛТ: сначала грузовые (pagetype=2), потом остальные
        qs = qs.order_by('-car_model__pagetype', '-created_at')

        # Поиск по тексту
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

        # Марка
        brand = g.get('brand')
        if brand:
            qs = qs.filter(Q(brand__iexact=brand) | Q(car_brand__name__iexact=brand))

        # Тип автомобиля (если явно выбран)
        pagetype = g.get('pagetype')
        if pagetype:
            qs = qs.filter(car_model__pagetype=pagetype)

        # Модель
        model_auto = g.get('model_auto')
        if model_auto:
            qs = qs.filter(model_auto__iexact=model_auto)

        # Топливо
        fuel = g.getlist('fuel')
        if fuel:
            qs = qs.filter(fuel__in=fuel)

        # Год
        year_min = g.get('year_min')
        year_max = g.get('year_max')
        if year_min:
            qs = qs.filter(year__gte=year_min)
        if year_max:
            qs = qs.filter(year__lte=year_max)

        # Пробег
        mileage_min = g.get('mileage_min')
        mileage_max = g.get('mileage_max')
        if mileage_min:
            qs = qs.filter(mileage__gte=mileage_min)
        if mileage_max:
            qs = qs.filter(mileage__lte=mileage_max)

        # Мощность
        power_min = g.get('power_min')
        power_max = g.get('power_max')
        if power_min:
            qs = qs.filter(power__gte=power_min)
        if power_max:
            qs = qs.filter(power__lte=power_max)

        # Объём двигателя
        engine_volume_min = g.get('engine_volume_min')
        engine_volume_max = g.get('engine_volume_max')
        if engine_volume_min:
            qs = qs.filter(engine_volume__gte=engine_volume_min)
        if engine_volume_max:
            qs = qs.filter(engine_volume__lte=engine_volume_max)

        # Двери
        doors = g.get('doors')
        if doors:
            qs = qs.filter(doors=doors)

        # Цвет
        color = g.get('color')
        if color:
            qs = qs.filter(color__iexact=color)

        # Наличие изображений
        has_images = g.get('has_images')
        if has_images:
            qs = qs.filter(images__isnull=False)

        # Коробка передач
        transmission = g.getlist('transmission')
        if transmission:
            qs = qs.filter(transmission__in=transmission)

        # Привод
        drive = g.getlist('drive')
        if drive:
            qs = qs.filter(drive__in=drive)

        # Цена
        price_min = g.get('price_min')
        price_max = g.get('price_max')
        if price_min:
            qs = qs.filter(price__gte=price_min)
        if price_max:
            qs = qs.filter(price__lte=price_max)

        # Пользовательская сортировка — ПЕРЕПИСЫВАЕТ дефолтную
        order = g.get('order')
        if order == 'price_asc':
            qs = qs.order_by('price')
        elif order == 'price_desc':
            qs = qs.order_by('-price')
        elif order == 'year_asc':
            qs = qs.order_by('year')
        elif order == 'year_desc':
            qs = qs.order_by('-year')
        elif order == 'mileage_asc':
            qs = qs.order_by('mileage')
        elif order == 'mileage_desc':
            qs = qs.order_by('-mileage')
        # else: оставляем дефолтный порядок (грузовые → остальные)

        return qs.select_related('car_model', 'car_brand')

    def get_context_data(self, **kwargs):
        from moderation.models import CarBrand, CarModel  # если нужно, подстрой путь
        context = super().get_context_data(**kwargs)
        g = self.request.GET

        selected_brand = g.get('brand')
        selected_pagetype = g.get('pagetype')
        try:
            pagetype_int = int(selected_pagetype) if selected_pagetype else None
        except ValueError:
            pagetype_int = None

        # Бренды и модели
        brands_qs = CarBrand.objects.all()
        models_qs = CarModel.objects.all()

        if pagetype_int:
            models_qs = models_qs.filter(pagetype=pagetype_int)
            brands_qs = brands_qs.filter(models__pagetype=pagetype_int).distinct()

        if selected_brand:
            models_qs = models_qs.filter(brand__name=selected_brand)

        context['brands'] = brands_qs.order_by('name')
        context['models'] = models_qs.order_by('name')

        # Остальные фильтры (из объявлений)
        filter_adverts_qs = Advert.objects.filter(published=True)

        context['currencies'] = (
            filter_adverts_qs
            .exclude(currency__isnull=True)
            .values_list('currency', flat=True)
            .distinct()
            .order_by('currency')
        )
        context['colors'] = (
            filter_adverts_qs
            .exclude(color__isnull=True)
            .values_list('color', flat=True)
            .distinct()
            .order_by('color')
        )
        context['doors'] = (
            filter_adverts_qs
            .exclude(doors__isnull=True)
            .values_list('doors', flat=True)
            .distinct()
            .order_by('doors')
        )

        context['pagetype_choices'] = CarModel.PAGE_CHOICE
        context['selected_pagetype'] = selected_pagetype or ''

        context['transmission_choices'] = Advert.TransmissionType.choices
        context['fuel_choices'] = Advert.FuelType.choices
        context['drive_choices'] = Advert.DriveType.choices
        context['selected_transmissions'] = g.getlist('transmission')
        context['selected_fuels'] = g.getlist('fuel')

        context['params'] = g
        return context



class AdvertDetailView(CustomHtmxMixin, DetailView):
    """Страница новости"""
    model = Advert
    template_name = 'site/useraccount/adverts_detail.html'
    context_object_name = 'advert'
    slug_field = "pk"


"""ЧаВо"""
class FaqsModerView(CustomHtmxMixin, ListView):
    model = Faqs
    template_name = 'site/useraccount/faqs.html'  # No .html extension
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



def create_application(request, advert_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            advert = Advert.objects.get(id=advert_id)

            application = AdvertAplication.objects.create(
                advert=advert,
                status=AdvertAplication.Status.NEW,
                price=0,
            )

            settings = SettingsGlobale.objects.first()

            # Перебираем номера файлов от 1 до 8
            for i in range(1, 9):
                file_field_name = f'document_file_{i}'
                file_obj = getattr(settings, file_field_name, None)
                if file_obj:
                    AdvertDocument.objects.create(
                        aplication=application,
                        file=file_obj,
                        document_type=2,
                        type=i,
                        name=file_obj.name,
                    )

            # 🔹 Админы (берём user из Profile)
            admin_users = [profile.user for profile in Profile.objects.filter(employee=4)]

            # Добавляем всех админов и текущего пользователя
            application.user.add(*admin_users, request.user)

            return JsonResponse({'success': True, 'application_id': str(application.id)})

        except Advert.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Объявление не найдено'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})



@login_required
def create_application_view(request, advert_id):
    """
    Создание заявки для текущего пользователя.
    Advert живёт в БД 'adverts',
    AdvertAplication и остальные модели — в default.
    """

    # 1. Забираем объявление из БД 'adverts'
    advert = get_object_or_404(
        Advert.objects.using("adverts"),
        id=advert_id
    )
    print(f"Найдено объявление {advert.id} из БД 'adverts'")

    try:
        # 2. Все изменения — в default
        with transaction.atomic(using="default"):
            # создаём заявку, теперь БЕЗ ForeignKey, используем advert_id / advert_name
            application = AdvertAplication.objects.using("default").create(
                advert_id=advert.id,
                advert_name=advert.name,
                price=Decimal("0.00"),
                status=AdvertAplication.Status.NEW,
            )
            print(f"Создана заявка: {application.id} (БД default)")

            # Настройки
            settings_obj = SettingsGlobale.objects.using("default").first()
            print(f"Настройки: {settings_obj}")

            # Документы
            documents_to_create = []
            if settings_obj:
                for i in range(1, 9):
                    file_field_name = f"document_file_{i}"
                    file_obj = getattr(settings_obj, file_field_name, None)

                    if file_obj and file_obj.name:
                        if default_storage.exists(file_obj.name):
                            documents_to_create.append(AdvertDocument(
                                aplication=application,
                                file=file_obj,
                                document_type=2,
                                type=i,
                                name=file_obj.name,
                            ))
                            print(f"Добавлен документ: {file_obj.name}")
                        else:
                            print(f"Файл не найден в хранилище: {file_obj.name}")

            if documents_to_create:
                AdvertDocument.objects.using("default").bulk_create(documents_to_create)
                print(f"Создано документов: {len(documents_to_create)}")
            else:
                print("Нет документов для создания")

            # Пользователи (Profile живёт в default)
            admin = Profile.objects.using("default").filter(employee=4).first()
            users_to_add = [request.user]

            if admin:
                users_to_add.append(admin)
                application.user_menager.add(admin)
                print(f"Добавлен менеджер: {admin}")

            application.user.set(users_to_add)
            print(f"Добавлены пользователи: {[user.username for user in users_to_add]}")

        messages.success(request, "Заявка успешно создана.")
        return redirect("moderation:my_applications")

    except IntegrityError as e:
        print(f"Ошибка целостности данных: {e}")
        messages.error(request, "Ошибка при создании заявки.")
        return redirect("moderation:my_applications")

    except Exception as e:
        print(f"Общая ошибка в create_application_view: {e}")
        messages.error(request, "Произошла непредвиденная ошибка.")
        return redirect("moderation:my_applications")


class ApplicationListView(CustomHtmxMixin, ListView):
    model = AdvertAplication
    template_name = 'site/useraccount/documents.html'
    context_object_name = 'documents'
    paginate_by = 10  # 10 заявок на страницу

    def get_queryset(self):
        # Получаем только те заявки, в которых участвует текущий пользователь
        queryset = super().get_queryset()

        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                # Пользователь может быть в любой из трех групп
                Q(user=self.request.user) |
                Q(user_menager=self.request.user) |
                Q(user_drivers=self.request.user)
            ).prefetch_related(
                'user_menager',
                'user_drivers'
            ).distinct()  # Добавляем distinct() чтобы избежать дубликатов

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем paginator и page_obj для совместимости с шаблоном
        paginator = Paginator(self.get_queryset(), self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context.update({
            'paginator': paginator,
            'page_obj': page_obj,
        })
        return context

    def get_seo_context(self):
        """
        Переопределяем SEO данные для страницы заявок
        """
        return {
            'block_title': 'Мои заявки',
            'block_description': 'Список моих заявок на перевозки',
            'block_propertytitle': 'Заявки на перевозку',
            'block_propertydescription': 'Управление заявками на перевозку грузов',
            'block_propertyimage': '',
            'block_head': ''
        }


@login_required
@require_POST
def send_message(request, app_id):
    application = get_object_or_404(AdvertAplication, id=app_id)
    content = request.POST.get('content')
    if content:
        message = ChatMessage.objects.create(
            applications=application,
            content=content,
            author=request.user,
        )
        return JsonResponse({
            'id': str(message.id),
            'author': message.author.username,
            'content': message.content,
            'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return JsonResponse({'error': 'Нет содержимого'}, status=400)


@login_required
def get_new_messages(request, app_id):
    application = get_object_or_404(AdvertAplication, id=app_id)
    last_message_id = request.GET.get('last_message_id')
    current_user = request.user

    if last_message_id:
        try:
            last_message = ChatMessage.objects.get(id=last_message_id)
            new_messages = ChatMessage.objects.filter(
                applications=application,
                date__gt=last_message.date
            ).exclude(author=current_user).order_by('date')
        except ChatMessage.DoesNotExist:
            new_messages = ChatMessage.objects.filter(
                applications=application
            ).exclude(author=current_user).order_by('date')
    else:
        new_messages = ChatMessage.objects.filter(
            applications=application
        ).exclude(author=current_user).order_by('date')

    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': str(msg.id),
            'author': msg.author.username,
            'content': msg.content,
            'date': msg.date.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return JsonResponse({'messages': messages_data})


def start_call(request, application_id):
    if request.method == 'POST':
        try:
            application = get_object_or_404(AdvertAplication, id=application_id)
            call_session = CallSession.objects.create(
                application=application,
                caller=request.user,
                callee=application.user.first()
            )
            call_id = call_session.id
            start_call_task.delay(call_id)
            return JsonResponse({'call_id': call_id})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error in start_call")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def generate_contract(request,application_id):
    pass
    # buffer = io.BytesIO()
    # c = canvas.Canvas(buffer, pagesize=A4)
    # width, height = A4
    #
    # doc_type = 1  # замените на ваш реальный тип документа
    # application = get_object_or_404(AdvertAplication, id=application_id)
    # advert = application.advert
    #
    # # Попытка загрузить файл-изображение для фона (если есть)
    # photo_path = None
    # print(application.documents.get(type=doc_type))
    #
    # try:
    #     photo_doc = application.documents.get(type=doc_type)
    #     photo_path = getattr(photo_doc, 'file', None)
    #     # если файл хранится как путь на диск
    #     if photo_path and hasattr(photo_path, 'path'):
    #         photo_path = photo_path.path
    # except Exception:
    #     photo_path = None
    #
    # if photo_path:
    #     c.drawImage(photo_path, 0, 0, width=width, height=height)
    #
    # y = height - 60
    # c.setFont("Helvetica-Bold", 18)
    # c.setFillColorRGB(0, 0, 0)
    # c.drawString(50, y, "ДОГОВОР КУПЛЛИ-ПРОДАЖИ ТОВАРА")
    # y -= 30
    #
    # c.setFont("Helvetica", 12)
    # c.drawString(50, y, f"Дата: {timezone.now().strftime('%d.%m.%Y')}")
    # y -= 40
    #
    # c.drawString(50, y, "Передаваемое транспортное средство:")
    # y -= 20
    #
    # data = [
    #     ("Марка", getattr(advert, 'brand', '')),
    #     ("Модель", getattr(advert, 'model_auto', '')),
    #     ("Год выпуска", getattr(advert, 'year', '')),
    #     ("Пробег", getattr(advert, 'mileage', '')),
    #     ("Цвет", getattr(advert, 'color', '')),
    #     ("Объем двигателя", getattr(advert, 'engine_volume', '')),
    #     ("Мощность", getattr(advert, 'power', '')),
    #     ("Тип КПП", advert.get_transmission_display() if hasattr(advert, 'get_transmission_display') else ''),
    #     ("Топливо", advert.get_fuel_display() if hasattr(advert, 'get_fuel_display') else ''),
    #     ("Привод", advert.get_drive_display() if hasattr(advert, 'get_drive_display') else ''),
    #     ("Адрес размещения", getattr(advert, 'address', '')),
    #     ("Цена", getattr(application, 'price', '')),
    # ]
    #
    # for label, value in data:
    #     if y < 40:
    #         c.showPage()
    #         y = height - 60
    #         if photo_path:
    #             c.drawImage(photo_path, 0, 0, width=width, height=height)
    #     c.drawString(60, y, f"{label}: {value}")
    #     y -= 16
    #
    # c.save()
    # buffer.seek(0)
    #
    # response = FileResponse(buffer, as_attachment=True, filename=f"contract_{application_id}.pdf")
    # response['Content-Type'] = 'application/pdf'
    # return response


@login_required
def call_page(request, application_id,calle_id):
    application = get_object_or_404(AdvertAplication, id=application_id)
    calle = Profile.objects.get(id=calle_id)
    call, created = CallSession.objects.get_or_create(
        application=application,
        is_active = True,
        defaults={
            'caller': request.user,
            'callee': calle
        }
    )

    if not call.callee:
        return HttpResponse("Нет пользователя для звонка", status=400)

    other_user = call.callee if request.user == call.caller else call.caller


    return render(request, 'site/useraccount/call_page.html', {
        'application_id': application_id,
        'call_id': str(call.id),
        'user': request.user,
        'is_call_page': True,
        'other_user': other_user,
    })

@login_required
def call_page_iframe(request, application_id,calle_id):
    application = get_object_or_404(AdvertAplication, id=application_id)
    calle = Profile.objects.get(id=calle_id)
    call, created = CallSession.objects.get_or_create(
        application=application,
        is_active = True,
        defaults={
            'caller': request.user,
            'callee': calle
        }
    )

    if not call.callee:
        return HttpResponse("Нет пользователя для звонка", status=400)

    other_user = call.callee if request.user == call.caller else call.caller


    return render(request, 'site/useraccount/call_page_iframe.html', {
        'application_id': application_id,
        'call_id': str(call.id),
        'user': request.user,
        'is_call_page': True,
        'other_user': other_user,
    })


@method_decorator(login_required, name='dispatch')
class CreateExpenseView(View):
    def post(self, request, *args, **kwargs):
        try:
            application_id = request.POST.get("application")
            title = request.POST.get("title")
            amount = request.POST.get("amount")
            date = datetime.now().date()

            # Проверка обязательных полей
            if not application_id or not title or not amount:
                return HttpResponseBadRequest("Не все данные переданы")

            # Преобразуем сумму в Decimal
            try:
                amount = Decimal(str(amount).replace(',', '.'))
            except Exception:
                return HttpResponseBadRequest("Сумма должна быть числом")

            # Получаем приложение
            application = get_object_or_404(AdvertAplication, id=application_id)

            # Проверка прав:

            # Создаём расход
            expense = AdvertExpense.objects.create(
                aplication=application,
                title=title,
                amount=amount,
                date=date,
                user=request.user
            )

            # Обновляем общую сумму расходов
            agg = application.expenses.aggregate(total=Sum('amount'))
            application.expenses_total = agg.get('total') or Decimal('0')
            application.save()

            # Рендерим новую строку таблицы
            expense_row = f'''
            <tr id="expense-{expense.id}">
                <td title="{expense.id}">{expense.title}</td>
                <td class="text-end">{expense.amount} $</td>
                <td>{expense.date.strftime('%d.%m.%Y')}</td>
            </tr>
            '''

            # Рендерим OOB-блоки
            sidebar_html = render_to_string(
                "moderation/partials/application_sidebar.html",
                {"application": application},
                request=request
            )
            activity_html = render_to_string(
                "moderation/partials/activity-list.html",
                {"application": application},
                request=request
            )
            balance_html = render_to_string(
                "moderation/partials/set-balanse.html",
                {"application": application},
                request=request
            )

            # Скрипт для HTMX + добавление строки
            response_html = f'''
                        <div id="application-finance" hx-swap-oob="innerHTML">{sidebar_html}</div>
            <div id="activity-list" hx-swap-oob="innerHTML">{activity_html}</div>
            <div id="set-balanse" hx-swap-oob="innerHTML">{balance_html}</div>

            <script>
                var tbody = document.getElementById('expensesList');
                if (tbody) {{
                    var emptyMsg = document.getElementById('emptyExpenses');
                    if (emptyMsg) emptyMsg.remove();
                    tbody.insertAdjacentHTML('beforeend', `{expense_row}`);
                }}

                // Обновляем OOB блоки
                htmx.ajax('GET', '{request.build_absolute_uri("/moderation/applications/" + str(application.id) + "/finance/")}', {{
                    target: '#application-finance',
                    swap: 'innerHTML'
                }});
                htmx.ajax('GET', '{request.build_absolute_uri("/moderation/applications/" + str(application.id) + "/activity/")}', {{
                    target: '#activity-list',
                    swap: 'innerHTML'
                }});

                // Закрываем модальное окно
                var modal = bootstrap.Modal.getInstance(document.getElementById('addExpenseModal'));
                if (modal) modal.hide();

                // Очищаем форму
                document.getElementById('add-expense-form').reset();
            </script>
            '''

            return HttpResponse(mark_safe(response_html))

        except PermissionDenied as e:
            return HttpResponseForbidden(str(e))
        except AdvertAplication.DoesNotExist:
            return HttpResponseBadRequest("Приложение не найдено")
        except Exception as e:
            return HttpResponseBadRequest(str(e))





@login_required
def check_active_call(request):
    user = request.user
    # Проверяем, есть ли активный звонок, где пользователь - это callee
    active_call = CallSession.objects.filter(callee=user, is_active=True).first()
    if active_call:
        # Можно вернуть информацию о звонке, например, его id или URL для iframe
        return JsonResponse({'has_active_call': True, 'call_id': str(active_call.application.id), 'calle_id': str(active_call.callee.id)})
    else:
        return JsonResponse({'has_active_call': False})


@csrf_exempt
def hangup_call(request, call_id):
    try:
        call_session = CallSession.objects.get(id=call_id)

        # Проверяем, имеет ли пользователь право удалить этот звонок
        if request.user not in [call_session.caller, call_session.callee]:
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

        # Удаляем звонок
        call_session.delete_call()

        return JsonResponse({'status': 'success', 'message': 'Call ended'})

    except CallSession.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Call not found'}, status=404)