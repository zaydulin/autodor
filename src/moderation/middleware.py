# moderation/middleware.py
import logging
from decimal import Decimal
from datetime import datetime, date, time

from django.apps import apps
from django.db import transaction
from django.forms.models import model_to_dict

logger = logging.getLogger(__name__)


def serialize_basic(val):
    """Сериализация простых типов для JSON (Decimal/datetime -> str)."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, (list, tuple, set)):
        return [serialize_basic(x) for x in val]
    if isinstance(val, dict):
        return {k: serialize_basic(v) for k, v in val.items()}
    return val


def dict_for_compare(instance):
    """
    Возвращает словарь полей модели для сравнения.
    FK -> pk, M2M -> [pk, pk...]
    """
    try:
        data = model_to_dict(instance)
        # Добавляем M2M вручную
        for field in getattr(instance._meta, "many_to_many", []):
            try:
                data[field.name] = list(getattr(instance, field.name).values_list("pk", flat=True))
            except Exception:
                data[field.name] = None
        return {k: serialize_basic(v) for k, v in data.items()}
    except Exception as e:
        logger.exception("dict_for_compare failed for %s: %s", getattr(instance, "pk", "?"), e)
        return {}


def resolve_fk_display(field, pk):
    """Если поле — FK, пытаемся вернуть str(объекта) по pk."""
    if pk is None:
        return None
    try:
        rel = getattr(field, "remote_field", None)
        if not rel:
            return pk
        model = rel.model
        obj = model.objects.filter(pk=pk).first()
        return str(obj) if obj is not None else str(pk)
    except Exception:
        return str(pk)


def resolve_m2m_display(field, pks):
    """Для M2M возвращаем список str() связанных объектов (по pk)."""
    if pks is None:
        return None
    try:
        rel = getattr(field, "remote_field", None)
        if not rel:
            return [str(x) for x in (pks or [])]
        model = rel.model
        objs = model.objects.filter(pk__in=pks)
        map_by_pk = {o.pk: o for o in objs}
        # сохраняем порядок pks
        return [str(map_by_pk.get(pk, pk)) for pk in pks]
    except Exception:
        return [str(x) for x in (pks or [])]


def readable_value(field, raw_value):
    """
    Преобразует сырое значение (pk / list of pks / scalar) в человеко-понятный вид.
    """
    # M2M
    if getattr(field, "many_to_many", False) or getattr(field, "m2m", False):
        return resolve_m2m_display(field, raw_value)

    # FK-like
    if getattr(field, "remote_field", None) and not getattr(field, "many_to_many", False):
        return resolve_fk_display(field, raw_value)

    # остальные значения уже сериализованы
    return raw_value


def human_readable_changes(model, instance, old_dict, new_dict):
    """
    Возвращает словарь:
    {
      "Поле verbose": {"action": "добавил", "new": ...}
      "Поле verbose": {"action": "изменил", "old": ..., "new": ...}
    }
    """
    changes = {}
    fields = list(getattr(model._meta, "fields", [])) + list(getattr(model._meta, "many_to_many", []))

    for field in fields:
        fname = field.name
        verbose = getattr(field, "verbose_name", fname)

        # пропускаем авто-поля времени и auto-created
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False) or getattr(field, "auto_created", False):
            continue

        old_val = None if old_dict is None else old_dict.get(fname)
        new_val = new_dict.get(fname)

        # если значения одинаковы — пропускаем
        if old_val == new_val:
            continue

        readable_old = readable_value(field, old_val)
        readable_new = readable_value(field, new_val)

        if old_dict is None:
            # создание объекта
            changes[str(verbose)] = {"action": "добавил", "new": readable_new}
        else:
            changes[str(verbose)] = {"action": "изменил", "old": readable_old, "new": readable_new}

    return changes if changes else None


def get_all_related_models():
    """
    Находим модели, связанных с AdvertAplication, и включаем саму AdvertAplication,
    но исключаем AdvertApplicationLog (чтобы не логировать записи логов).
    """
    try:
        AdvertAplication = apps.get_model("moderation", "AdvertAplication")
    except LookupError:
        return []

    try:
        AdvertApplicationLog = apps.get_model("moderation", "AdvertApplicationLog")
    except LookupError:
        AdvertApplicationLog = None

    related = []

    # включаем саму AdvertAplication в мониторинг
    related.append(AdvertAplication)

    # модели, у которых есть FK на AdvertAplication
    for model in apps.get_models():
        if model == AdvertAplication or (AdvertApplicationLog and model == AdvertApplicationLog):
            continue
        try:
            for field in model._meta.get_fields():
                if getattr(field, "related_model", None) == AdvertAplication:
                    related.append(model)
                    break
        except Exception:
            continue

    # модели, на которые AdvertAplication ссылается (FK/M2M)
    try:
        for field in AdvertAplication._meta.get_fields():
            rel = getattr(field, "related_model", None)
            if rel and rel != AdvertAplication and (not AdvertApplicationLog or rel != AdvertApplicationLog) and rel not in related:
                related.append(rel)
    except Exception:
        pass

    # уникализируем
    unique = []
    seen = set()
    for m in related:
        # фильтруем None и дубликаты
        if m is None:
            continue
        key = f"{m._meta.app_label}.{m._meta.model_name}"
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


# Глобальный список моделей, которые мониторим
RELATED_MODELS = get_all_related_models()


def find_application_from_instance(instance):
    """
    Пытаемся найти связанный AdvertAplication для любого объекта.
    Если instance сам AdvertAplication — возвращаем его.
    """
    try:
        AdvertAplication = apps.get_model("moderation", "AdvertAplication")
    except LookupError:
        return None

    if isinstance(instance, AdvertAplication):
        return instance

    # прямые FK-поля
    for field in getattr(instance, "_meta").get_fields():
        if getattr(field, "related_model", None) == AdvertAplication:
            try:
                val = getattr(instance, field.name)
                if val:
                    return val
            except Exception:
                continue

    # стандартные имена полей
    for name in ("application", "aplication", "app", "advert_application"):
        val = getattr(instance, name, None)
        if val and hasattr(val, "_meta"):
            return val

    # обратные связи (редкий случай) — пробуем найти AdvertAplication через related_name
    try:
        for field in getattr(AdvertAplication, "_meta").get_fields():
            rel = getattr(field, "related_model", None)
            if rel == instance.__class__:
                related_name = getattr(field, "related_name", None) or instance.__class__.__name__.lower() + "_set"
                manager = getattr(instance, related_name, None)
                if manager and hasattr(manager, "all") and manager.all().exists():
                    return manager.all().first()
    except Exception:
        pass

    return None


def get_user_from_request(request):
    user = getattr(request, "user", None)
    if user and hasattr(user, "is_authenticated") and user.is_authenticated:
        return user
    return None


class AdvertApplicationLogMiddleware:
    """
    Middleware: снимает snapshot перед изменениями и создаёт лог после.
    Логирует изменения моделей из RELATED_MODELS (включая AdvertAplication),
    но не создаёт логов для AdvertApplicationLog.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.snapshots = {}

    def __call__(self, request):
        method = request.method.upper()
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            self.take_snapshots()
        response = self.get_response(request)
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            self.create_logs(request)
        return response

    def take_snapshots(self):
        """Снимаем snapshot всех объектов в RELATED_MODELS"""
        self.snapshots = {}
        for model in RELATED_MODELS:
            try:
                for obj in model.objects.all():
                    try:
                        self.snapshots[(model, obj.pk)] = dict_for_compare(obj)
                    except Exception as e:
                        logger.exception(
                            "Snapshot per-object failed for %s.%s pk=%s: %s",
                            model._meta.app_label, model._meta.model_name, getattr(obj, "pk", None), e
                        )
            except Exception as e:
                logger.exception("Snapshot failed for model %s: %s", getattr(model, "_meta", None), e)

    def create_logs(self, request):
        user = get_user_from_request(request)
        for model in RELATED_MODELS:
            # дополнительная защита: не логируем модель логов
            if model and getattr(model._meta, "model_name", "") == "advertapplicationlog":
                continue

            verbose_model = getattr(model._meta, "verbose_name", model._meta.model_name)
            try:
                for obj in model.objects.all():
                    key = (model, obj.pk)
                    old = self.snapshots.get(key)  # None => создание объекта
                    new = dict_for_compare(obj)
                    changes = human_readable_changes(model, obj, old, new)
                    if not changes:
                        continue

                    action = "create" if old is None else "update"
                    application = find_application_from_instance(obj)
                    if not application:
                        # если не удалось связать с заявкой — пропускаем
                        continue

                    payload = {
                        "application": application,
                        "related_model": str(verbose_model),
                        "related_object_id": str(obj.pk),
                        "action": action,
                        "user": user,
                        "changes": changes
                    }

                    try:
                        transaction.on_commit(lambda payload=payload: self._create_log(payload))
                    except Exception:
                        # если on_commit не доступен (редко) — создаём сразу
                        self._create_log(payload)

            except Exception as e:
                logger.exception("Error while scanning objects of model %s: %s", model, e)

    def _create_log(self, payload):
        """Создаём запись AdvertApplicationLog"""
        try:
            AdvertApplicationLog = apps.get_model("moderation", "AdvertApplicationLog")
        except LookupError:
            logger.error("AdvertApplicationLog model not found. Cannot create log.")
            return

        try:
            AdvertApplicationLog.objects.create(
                application=payload["application"],
                related_model=payload["related_model"],
                related_object_id=payload["related_object_id"],
                action=payload["action"],
                user=payload["user"],
                changes=payload["changes"]
            )
        except Exception as e:
            logger.exception("Failed to create AdvertApplicationLog entry: %s", e)
