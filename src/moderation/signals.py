import json
import os
from decimal import Decimal, InvalidOperation  # <-- стандартный Decimal
from urllib.parse import urlparse

from django.db import transaction
from django.db.models.signals import m2m_changed
from django.contrib.contenttypes.models import ContentType

import requests
from django.core.files.base import ContentFile
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .models import AdvertDocument, AdvertAplication, AdvertApplicationImage, Advert, WalletDriver, AdvertExpense, AdvertApplicationLog
from webmain.models import SettingsGlobale
import logging

from useraccount.models import Notification

from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields import NOT_PROVIDED


def determine_notification_type_default():
    """
    Безопасно определить, какое значение поставить в Notification.type чтобы не получить IntegrityError.
    Логика:
      - если поле отсутствует -> вернуть None (не передавать)
      - если есть default != NOT_PROVIDED -> вернуть его
      - если поле.null -> вернуть None
      - если есть choices -> вернуть first choice value
      - иначе -> вернуть 0 (fallback)
    """
    try:
        field = Notification._meta.get_field("type")
    except FieldDoesNotExist:
        return None

    try:
        default = field.get_default()
    except Exception:
        default = getattr(field, "default", NOT_PROVIDED)

    if default is not NOT_PROVIDED and default is not None:
        return default

    if getattr(field, "null", False):
        return None

    choices = getattr(field, "choices", None)
    if choices:
        try:
            return choices[0][0]
        except Exception:
            pass

    return 0


NOTIFICATION_TYPE_DEFAULT = determine_notification_type_default()


def make_summary(payload: dict) -> str:
    """
    Короткий человекопонятный текст (summary) для показа в списке уведомлений.
    Возьмём: "<related_model> — <action>. Кто: <user_who>. [короткие изменения]"
    changes коротко: первые 3 изменений в одну строку.
    """
    try:
        related_model = payload.get("related_model", "")
        action = payload.get("action", "")
        user_who = payload.get("user_who", "Система")
        app_ident = payload.get("application", {}).get("order_number") or payload.get("application", {}).get("id") or ""
        changes = payload.get("changes") or {}
        # собираем первые 3 полей изменений в краткую строку
        short_parts = []
        for i, (field, info) in enumerate(changes.items()):
            if i >= 3:
                break
            if isinstance(info, dict):
                act = info.get("action")
                if act == "добавил":
                    short_parts.append(f"{field}: +{info.get('new')}")
                elif act == "изменил":
                    short_parts.append(f"{field}: {info.get('old')}→{info.get('new')}")
                else:
                    short_parts.append(f"{field}")
            else:
                short_parts.append(f"{field}: {info}")
        short_changes = "; ".join(short_parts)
        summary = f"{related_model} — {action}. Кто: {user_who}. Заявка: {app_ident}."
        if short_changes:
            summary = f"{summary} {short_changes}"
        return summary
    except Exception:
        return ""


@receiver(post_save, sender=AdvertApplicationLog)
def advert_application_log_post_save(sender, instance: AdvertApplicationLog, created, **kwargs):
    """
    После создания AdvertApplicationLog создаём Notification для всех пользователей заявки.
    Notification.message будет содержать JSON-представление payload:
    {
      related_model, related_object_id, action, user_who,
      application: {id, order_number},
      changes: { ... }  # полный dict как в log.changes
      text: <summary короткий человекопонятный>
    }
    """
    if not created:
        return

    try:
        application = instance.application
    except Exception:
        logger.exception("AdvertApplicationLog without application (pk=%s)", getattr(instance, "pk", None))
        return

    # Собираем всех пользователей
    users_set = set()
    try:
        users_set.update(application.user.all())
    except Exception:
        pass
    try:
        users_set.update(application.user_menager.all())
    except Exception:
        pass
    try:
        users_set.update(application.user_drivers.all())
    except Exception:
        pass

    if not users_set:
        return

    # Кто сделал действие
    try:
        if instance.user:
            user_who = (instance.user.get_full_name() or instance.user.username) if hasattr(instance.user, "get_full_name") else str(instance.user)
        else:
            user_who = "Система"
    except Exception:
        user_who = "Система"

    # Формируем payload
    payload = {
        "related_model": instance.related_model,
        "related_object_id": instance.related_object_id,
        "action": instance.action,
        "log_id": str(instance.id),
        "user_who": user_who,
        "application": {
            "id": str(application.id),
            "order_number": getattr(application, "order_number", None),
        },
        "changes": instance.changes or {},
    }

    # Краткий человекопонятный текст
    payload["text"] = make_summary(payload)

    # JSON-сериализация (utf-8, сохранение русских букв)
    try:
        message_json = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        # fallback — stringify
        try:
            message_json = json.dumps({"text": payload.get("text", ""), "payload_str": str(payload)}, ensure_ascii=False)
        except Exception:
            message_json = json.dumps({"text": "Есть обновления"}, ensure_ascii=False)

    # ContentType: для связи можно указать тип заявки (AdvertAplication) — удобнее, чем тип лога
    try:
        ct = ContentType.objects.get_for_model(application.__class__)
    except Exception:
        ct = None

    # Подготовим Notification объекты
    notifs = []
    for user in users_set:
        try:
            kw = {
                "status": 1,
                "user": user,
                "content_type": ct,
                "object_id": 0,  # т.к. object_id PositiveIntegerField, ставим 0; можно изменить модель Notification при необходимости
                "message": message_json,
            }
            # Подставляем type, если нужно
            if NOTIFICATION_TYPE_DEFAULT is not None:
                kw["type"] = NOTIFICATION_TYPE_DEFAULT

            n = Notification(**kw)
            notifs.append(n)
        except Exception:
            logger.exception("Failed to prepare Notification for user %s (app=%s)", getattr(user, "pk", None), payload["application"]["id"])

    if not notifs:
        return

    def _bulk_create():
        try:
            Notification.objects.bulk_create(notifs)
        except Exception:
            for n in notifs:
                try:
                    n.save()
                except Exception:
                    logger.exception("Failed to save Notification for user %s", getattr(n.user, "pk", None))

    try:
        transaction.on_commit(_bulk_create)
    except Exception:
        _bulk_create()



# Логирование
logger = logging.getLogger(__name__)
#
# @receiver(m2m_changed, sender=AdvertAplication.user_menager.through)
# def update_user_from_menager(sender, instance, action, pk_set, **kwargs):
#     """
#     Обновляет поле user при изменении user_menager
#     Добавляет менеджеров в user, но не удаляет других пользователей
#     """
#     if action == "post_add":
#         # Добавляем новых менеджеров в поле user
#         new_managers = instance.user_menager.all()
#         current_users = set(instance.user.all())
#
#         # Добавляем только тех, кого еще нет в user
#         for manager in new_managers:
#             if manager not in current_users:
#                 instance.user.add(manager)
#
#     elif action == "post_remove":
#         # Удаляем менеджеров из user только если их нет в user_drivers
#         removed_manager_ids = pk_set
#         current_drivers = set(instance.user_drivers.values_list('id', flat=True))
#
#         # Удаляем только тех менеджеров, которые не являются водителями
#         for manager_id in removed_manager_ids:
#             if manager_id not in current_drivers:
#                 instance.user.remove(manager_id)
#
#
# @receiver(m2m_changed, sender=AdvertAplication.user_drivers.through)
# def update_user_from_drivers(sender, instance, action, pk_set, **kwargs):
#     """
#     Обновляет поле user при изменении user_drivers
#     Добавляет водителей в user, но не удаляет других пользователей
#     """
#     if action == "post_add":
#         # Добавляем новых водителей в поле user
#         new_drivers = instance.user_drivers.all()
#         current_users = set(instance.user.all())
#
#         # Добавляем только тех, кого еще нет в user
#         for driver in new_drivers:
#             if driver not in current_users:
#                 instance.user.add(driver)
#
#     elif action == "post_remove":
#         # Удаляем водителей из user только если их нет в user_menager
#         removed_driver_ids = pk_set
#         current_managers = set(instance.user_menager.values_list('id', flat=True))
#
#         # Удаляем только тех водителей, которые не являются менеджерами
#         for driver_id in removed_driver_ids:
#             if driver_id not in current_managers:
#                 instance.user.remove(driver_id)


def safe_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")

@receiver(post_save, sender=AdvertExpense)
def update_application_and_wallet(sender, instance, created, **kwargs):
    if not created:
        return

    expense = instance
    application = expense.aplication

    amount = safe_decimal(expense.amount)
    current_balance = safe_decimal(application.current_balance)
    expenses_total = safe_decimal(application.expenses_total)

    # Обновляем заявку
    application.expenses_total = expenses_total + amount
    application.current_balance = current_balance - amount
    application.save(update_fields=["expenses_total", "current_balance"])

    # Если пользователь — водитель заявки, обновляем кошелёк
    if expense.user and expense.user in application.user_drivers.all():
        wallet, _ = WalletDriver.objects.get_or_create(
            aplication=application,
            responsible=expense.user,
            defaults={
                "balance": Decimal("0"),
                "spent": Decimal("0"),
                "remainder": Decimal("0")
            }
        )

        wallet.spent = safe_decimal(wallet.spent) + amount
        wallet.remainder = safe_decimal(wallet.remainder) - amount
        wallet.save(update_fields=["spent", "remainder"])
















# В сигнале
@receiver(pre_save, sender=Advert)
def check_images_before_save(sender, instance, **kwargs):
    """
    Сигнал для проверки ссылок на изображения.
    Если нет валидных изображений, не сохраняем поле вообще.
    """
    if hasattr(instance, 'images') and instance.images:
        valid_images = []
        for image_url in instance.images:
            try:
                response = requests.head(image_url, allow_redirects=True, timeout=5)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if content_type and content_type.startswith('image/'):
                        valid_images.append(image_url)
            except requests.RequestException:
                continue

        if valid_images:
            instance.images = valid_images
        else:
            # Удаляем атрибут (поле не будет сохранено в БД)
            instance.images = None


def default_settings_file():
    settings = SettingsGlobale.objects.first()
    if not settings:
        return None
    for idx in range(1, 9):
        f = getattr(settings, f"document_file{idx}", None)
        if f and getattr(f, "name", ""):
            return f
    return None

@receiver(pre_save, sender=AdvertDocument)
def fill_document_file_from_settings(sender, instance, **kwargs):
    if instance.file and instance.file.name:
        return #
    default_file = default_settings_file()
    if not default_file:
        return

    try:
        with default_file.open("rb") as fp:
            content = fp.read()
            instance.file.save(os.path.basename(default_file.name), ContentFile(content), save=False)
    except Exception:
        pass

# @receiver(post_save, sender=AdvertAplication)
# def download_advert_images(sender, instance, created, **kwargs):
#     if not created:
#         return  # Обрабатываем только создание заявки
#
#     advert = instance.advert
#     images_urls = advert.images or []
#
#     for url in images_urls:
#         try:
#             response = requests.get(url)
#             response.raise_for_status()
#
#             # Получить имя файла из URL
#             parsed_url = urlparse(url)
#             filename = os.path.basename(parsed_url.path)
#             if not filename:
#                 filename = 'image.jpg'
#
#             # Создать объект ContentFile
#             image_content = ContentFile(response.content)
#
#             # Создать и сохранить изображение
#             advert_image = AdvertApplicationImage(application=instance)
#             advert_image.image.save(filename, image_content, save=True)
#
#         except Exception as e:
#             # Логировать ошибку или пропустить
#             print(f"Ошибка при скачивании {url}: {e}")
#
#


