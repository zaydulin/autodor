# moderation/middleware.py
import uuid
import logging
from decimal import Decimal
from datetime import datetime, date, time

from django.apps import apps
from django.db import transaction
from django.forms.models import model_to_dict

logger = logging.getLogger(__name__)


def serialize_value(val):
    """Преобразуем значение для JSONField"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if hasattr(val, 'pk') and hasattr(val, '_meta'):
        return f"{val._meta.model_name}:{val.pk}"
    if isinstance(val, (list, tuple)):
        return [serialize_value(x) for x in val]
    if isinstance(val, dict):
        return {k: serialize_value(v) for k, v in val.items()}
    return str(val)


def dict_for_compare(instance):
    """Создать словарь всех полей модели с сериализацией"""
    try:
        data = model_to_dict(instance)
        return {k: serialize_value(v) for k, v in data.items()}
    except Exception:
        return {}


def get_all_related_models():
    """Список всех моделей, связанных с AdvertAplication"""
    try:
        AdvertAplication = apps.get_model('moderation', 'AdvertAplication')
    except LookupError:
        return []

    related = []

    for model in apps.get_models():
        if model == AdvertAplication:
            continue
        for field in model._meta.get_fields():
            if getattr(field, 'related_model', None) == AdvertAplication:
                related.append(model)
                break

    for field in AdvertAplication._meta.get_fields():
        rel = getattr(field, 'related_model', None)
        if rel and rel != AdvertAplication and rel not in related:
            related.append(rel)

    # Убираем дубликаты
    unique = []
    seen = set()
    for m in related:
        key = f"{m._meta.app_label}.{m._meta.model_name}"
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


RELATED_MODELS = get_all_related_models()


def find_application_from_instance(instance):
    try:
        AdvertAplication = apps.get_model('moderation', 'AdvertAplication')
    except LookupError:
        return None

    if isinstance(instance, AdvertAplication):
        return instance

    # Прямые FK
    for field in instance._meta.get_fields():
        if getattr(field, 'related_model', None) == AdvertAplication:
            val = getattr(instance, field.name, None)
            if val:
                return val

    # Обратные связи
    for field in AdvertAplication._meta.get_fields():
        if getattr(field, 'related_model', None) == instance.__class__:
            related_name = field.name
            manager = getattr(instance, related_name, None)
            if manager and hasattr(manager, 'all') and manager.all().exists():
                return manager.all().first()

    for name in ('application', 'aplication', 'app', 'advert_application'):
        val = getattr(instance, name, None)
        if val and hasattr(val, '_meta'):
            return val

    return None


def get_user_from_request(request):
    user = getattr(request, 'user', None)
    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        return user
    return None


class AdvertApplicationLogMiddleware:
    """
    Middleware для логирования изменений связанных моделей с AdvertAplication
    с подробным описанием изменений.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.snapshots = {}  # хранение состояния объектов до изменений

    def __call__(self, request):
        if request.method.upper() in ('POST', 'PUT', 'PATCH', 'DELETE'):
            self.take_snapshots()
        response = self.get_response(request)
        if request.method.upper() in ('POST', 'PUT', 'PATCH', 'DELETE'):
            self.create_logs(request)
        return response

    def take_snapshots(self):
        self.snapshots = {}
        for model in RELATED_MODELS:
            try:
                for obj in model.objects.all():
                    self.snapshots[(model, obj.pk)] = dict_for_compare(obj)
            except Exception as e:
                logger.exception("Snapshot failed for %s: %s", model, e)

    def create_logs(self, request):
        user = get_user_from_request(request)
        for model in RELATED_MODELS:
            try:
                for obj in model.objects.all():
                    old = self.snapshots.get((model, obj.pk))
                    new = dict_for_compare(obj)
                    changes = None
                    action = None

                    if old is None:
                        # Новый объект
                        changes = {"old": None, "new": new}
                        action = "create"
                    else:
                        # Сравнение полей
                        diff = {}
                        for k, v_new in new.items():
                            v_old = old.get(k)
                            if v_old != v_new:
                                diff[k] = {"old": v_old, "new": v_new}
                        if diff:
                            changes = diff
                            action = "update"
                        else:
                            continue  # без изменений

                    # Находим application
                    application = find_application_from_instance(obj)
                    if not application:
                        continue

                    # Создаем лог
                    data = {
                        "application": application,
                        "related_model": model._meta.model_name,
                        "related_object_id": str(obj.pk),
                        "action": action,
                        "user": user,
                        "changes": changes
                    }
                    try:
                        transaction.on_commit(lambda data=data: self._create_log(data))
                    except Exception:
                        self._create_log(data)
            except Exception as e:
                logger.exception("Error logging model %s: %s", model, e)

    def _create_log(self, data):
        try:
            AdvertApplicationLog = apps.get_model('moderation', 'AdvertApplicationLog')
            AdvertApplicationLog.objects.create(
                application=data["application"],
                related_model=data["related_model"],
                related_object_id=data["related_object_id"],
                action=data["action"],
                user=data["user"],
                changes=data["changes"]
            )
        except Exception as e:
            logger.exception("Failed to create AdvertApplicationLog: %s", e)
