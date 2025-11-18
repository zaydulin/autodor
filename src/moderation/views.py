import base64
import io
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models.functions import TruncDate
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from moderation.tasks import start_call_task, end_call_task
from django.contrib.auth.mixins import UserPassesTestMixin

from django.contrib.auth.decorators import login_required
from django.db import models, transaction, IntegrityError
from django.http import JsonResponse, HttpResponse, HttpResponseServerError, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.db.models import Q, Prefetch
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import PathForm, PathResponsibilityForm, AdvertAplicationGalleryForm
from .models import AdvertAplication, ChatMessage, CallSession, AdvertDocument, AdvertExpense, AdvertApplicationImage, \
    CarModel, CarBrand, AdvertAplicationGallery, ExpenseMask,AdvertAplicationGalleryGroup,CartVod
from moderation.models import Advert, AdvertAplication,Path,PathResponsibility, Withdrawal
from webmain.models import Faqs, Seo
from useraccount.models import Profile

from webmain.models import SettingsGlobale
from django.db.models import Sum


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


class AdvertStatisticsView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        applications = AdvertAplication.objects.all().order_by('created_at')

        paginator = Paginator(applications, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        total_expenses_all = 0
        total_withdrawals_all = 0

        for application in applications:
            total_expenses = application.expenses.aggregate(Sum('amount'))['amount__sum'] or 0
            total_withdrawals = Withdrawal.objects.filter(application=application).aggregate(Sum('amount'))['amount__sum'] or 0
            total_expenses_all += total_expenses
            total_withdrawals_all += total_withdrawals

        # --- данные для графика ---
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

        context = {
            'page_obj': page_obj,
            'total_expenses_all': total_expenses_all,
            'total_withdrawals_all': total_withdrawals_all,
            'chart_labels': chart_labels,
            'chart_prices': chart_prices,
            'chart_expenses': chart_expenses,
            'chart_withdrawals': chart_withdrawals,
        }
        return render(request, 'advert_statistics.html', context)

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
    files = request.FILES.getlist("files[]")  # multiple input
    report_description = request.POST.get("report_description", "")

    if not title or not files:
        return JsonResponse({"success": False, "error": "Название и файлы обязательны"}, status=400)

    # 1. Создаём группу
    group = AdvertAplicationGalleryGroup.objects.create(
        application=application,
        title=title,
        description=description,
        position=application.gallery_groups.count() + 1,
    )

    items_data = []
    for f in files:
        item = AdvertAplicationGallery.objects.create(
            application=application,
            group=group,
            file=f,
            description=report_description,
            uploaded_by=request.user,
        )
        items_data.append({
            "id": item.id,
            "url": item.file.url,
            "description": item.description,
            "is_image": item.is_image,
            "is_video": item.is_video,
            "uploaded_at": item.uploaded_at.strftime("%d.%m.%Y %H:%M"),
        })

    return JsonResponse({
        "success": True,
        "group": {
            "id": group.id,
            "title": group.title,
            "description": group.description,
        },
        "items": items_data,
    })


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



class AdvertAplicationListView(LoginRequiredMixin, ListView):
    model = AdvertAplication
    template_name = "site/useraccount/advertaplication.html"
    context_object_name = "advertaplications"
    paginate_by = 20

    def get_queryset(self):
        # фильтруем M2M по текущему пользователю
        return (
            AdvertAplication.objects.filter(user=self.request.user)
            .select_related("advert")
            .prefetch_related("user")
            .order_by("-created_at")
        )

def expense_masks_json(request):
    """Вернёт все маски в JSON для автодополнения"""
    q = request.GET.get("q", "")
    masks = ExpenseMask.objects.all()
    if q:
        masks = masks.filter(name__icontains=q)
    return JsonResponse({"results": [m.name for m in masks[:20]]})


class AdvertAplicationDetailView(LoginRequiredMixin, DetailView):
    model = AdvertAplication
    template_name = "site/useraccount/advertaplication-detail.html"
    context_object_name = "application"

    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(user=self.request.user)
            .select_related("advert")
            .prefetch_related("user")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.object
        advert = application.advert

        # добавляем объявление
        context["application"] = application
        context["advert"] = advert
        expenses = application.expenses.all()
        context['expenses'] = expenses
        total_expenses = sum(expense.amount for expense in expenses)
        users_list = (
                list(application.user.all()) +
                list(application.user_menager.all()) +
                list(application.user_drivers.all())
        )
        context['users'] = [user for user in users_list if user != self.request.user]
        context['total_price'] =  advert.price
        context['total_expenses'] =  total_expenses
        context['total_ost'] = advert.price  - total_expenses

        application.price = context['total_ost']
        application.save()

        user = application.user.first()
        messages = ChatMessage.objects.filter(
            applications=application
        ).filter(
            Q(author=user) |
            Q(author__in=application.user_menager.all()) |
            Q(author__in=application.user_drivers.all())
        ).order_by('date')  # сортируем по времени
        context['messages'] = messages

        calls = CallSession.objects.filter(application=application)
        context['documents'] = application.documents.all().order_by('-created_at')
        context['calls'] = calls
        context['expense_masks'] = ExpenseMask.objects.all()

        context['all_managers'] = Profile.objects.filter(type=0,employee=2)
        context['all_drivers'] = Profile.objects.filter(type=0,employee=1)
        paths =  Path.objects.filter(aplication=application)
        context['paths'] = paths
        context['path_responsibilitys'] = PathResponsibility.objects.filter(path_choice__in=paths)

        # ✅ создаём экземпляры форм и передаём application_id
        context['path_form'] = PathForm(application_id=application.id)
        context['path_responsibilitys_form'] = PathResponsibilityForm(application_id=application.id)

        return context


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


@csrf_exempt
@require_http_methods(["POST"])
def create_responsibility(request):
    try:
        data = json.loads(request.body)
        application_id = data.get("application_id")  # 👈 достаём id заявки

        form = PathResponsibilityForm(data, application_id=application_id)  # 👈 передаём в форму

        if form.is_valid():
            responsibility = form.save()
            return JsonResponse({
                'success': True,
                'responsibility': {
                    'id': responsibility.id,
                    'status': responsibility.status,
                    'additional': responsibility.additional,
                    'responsible': {
                        'id': responsibility.responsible.id,
                        'name': f"{responsibility.responsible.first_name} {responsibility.responsible.last_name}"
                    }
                }
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def update_responsibility(request, responsibility_id):
    try:
        responsibility = get_object_or_404(PathResponsibility, id=responsibility_id)
        data = json.loads(request.body)
        form = PathResponsibilityForm(data, instance=responsibility)

        if form.is_valid():
            responsibility = form.save()
            return JsonResponse({
                'success': True,
                'responsibility': {
                    'id': responsibility.id,
                    'status': responsibility.status,
                    'additional': responsibility.additional
                }
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_responsibility(request, responsibility_id):
    try:
        responsibility = get_object_or_404(PathResponsibility, id=responsibility_id)
        responsibility.delete()
        return JsonResponse({'success': True})
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

@csrf_exempt
def update_application(request, application_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            application = AdvertAplication.objects.get(id=application_id)


            if 'status' in data:
                application.status = data['status']

            # Обработка ManyToMany полей
            if 'user_menager' in data:
                menager_ids = data['user_menager']
                menagers = Profile.objects.filter(id__in=menager_ids)
                # Очищаем текущие связи и добавляем новых
                application.user_menager.set(menagers)

            if 'user_drivers' in data:
                driver_ids = data['user_drivers']
                drivers = Profile.objects.filter(id__in=driver_ids)
                # Очищаем текущие связи и добавляем новых
                application.user_drivers.set(drivers)

            # Обновляем связанные пользователи, если есть
            if 'user' in data:
                user_ids = data['user']
                users = Profile.objects.filter(id__in=user_ids)
                application.user.set(users)

            if 'delevery_price' in data:
                delevery_price = data['delevery_price']
                delevery_price = int(delevery_price)
                application.delevery_price = delevery_price

            application.save()

            return JsonResponse({'success': True})

        except AdvertAplication.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Заявка не найдена'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False})


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


class AdvertDetailView(DetailView):
    """Страница новости"""
    model = Advert
    template_name = 'site/useraccount/adverts_detail.html'
    context_object_name = 'advert'
    slug_field = "pk"


"""ЧаВо"""
class FaqsModerView(ListView):
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
@transaction.atomic
def create_application_view(request, advert_id):
    """Создание заявки для текущего пользователя - исправленная версия"""
    try:
        advert = get_object_or_404(Advert, id=advert_id)

        # Создаем заявку с явным указанием статуса
        application = AdvertAplication.objects.create(
            advert=advert,
            price=0,
            status=AdvertAplication.Status.NEW  # ✅ Явно указываем статус
        )

        print(f"Создана заявка: {application.id}")

        # Получаем настройки
        settings = SettingsGlobale.objects.first()
        print(f"Настройки: {settings}")

        # Создаем документы только если settings существует
        documents_to_create = []
        if settings:
            for i in range(1, 9):
                file_field_name = f'document_file_{i}'
                file_obj = getattr(settings, file_field_name, None)

                # Проверяем, что файл существует и валиден
                if file_obj and file_obj.name:
                    # Проверяем существование файла в хранилище
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

        # Bulk создание документов
        if documents_to_create:
            AdvertDocument.objects.bulk_create(documents_to_create)
            print(f"Создано документов: {len(documents_to_create)}")
        else:
            print("Нет документов для создания")

        # Добавляем пользователей
        admin = Profile.objects.filter(employee=4).first()
        users_to_add = [request.user]

        if admin:
            users_to_add.append(admin)
            # ✅ Сначала сохраняем заявку, потом добавляем связи
            application.user_menager.add(admin)
            print(f"Добавлен менеджер: {admin}")

        application.user.set(users_to_add)
        print(f"Добавлены пользователи: {[user.username for user in users_to_add]}")

        # ⚠️ УБИРАЕМ обновление объявления - это основная проблема
        # advert.published = False
        # advert.save()  # ❌ ЭТО ОБНОВЛЯЕТ ДАННЫЕ МОДЕЛИ Advert

        print(f"Объявление НЕ обновлялось - published остался прежним")

        return redirect("moderation:my_applications")

    except IntegrityError as e:
        print(f"Ошибка целостности данных: {e}")
        # Здесь можно добавить логирование или отображение ошибки пользователю
        return redirect("error_page")
    except Exception as e:
        print(f"Общая ошибка: {e}")
        return redirect("error_page")

def application_list(request):
    # Получаем только те заявки, в которых участвует текущий пользователь
    applications = AdvertAplication.objects.filter(
        # Пользователь может быть в любой из трех групп
        Q(user=request.user) |
        Q(user_menager=request.user) |
        Q(user_drivers=request.user)
    ).prefetch_related(
        'user_menager',
        'user_drivers'
    ).distinct()  # Добавляем distinct() чтобы избежать дубликатов

    # Создаем пагинатор
    paginator = Paginator(applications, 10)  # 10 заявок на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'site/useraccount/documents.html',
        {
            'page_obj': page_obj,
            'paginator': paginator,
            'documents': page_obj,  # для совместимости с шаблоном
        }
    )

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
    def post(self, request):
        try:
            # Парсим JSON данные
            data = json.loads(request.body)

            # Получаем данные из запроса
            application_id = data.get('application')
            title = data.get('title')
            amount = data.get('amount')
            date = datetime.now()

            # Проверяем права доступа
            application = AdvertAplication.objects.get(id=application_id)
            if request.user not in application.user_menager.all() and request.user.employee != 4:
                raise PermissionDenied("У вас нет прав на добавление расходов")

            # Создаем новый расход
            expense = AdvertExpense.objects.create(
                aplication=application,
                title=title,
                amount=amount,
                date=date
            )



            return JsonResponse({
                'success': True,
                'message': 'Расход успешно добавлен',
                'expense_id': expense.id
            }, status=201)


        except PermissionDenied as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=403)

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