from datetime import timedelta

from celery import shared_task
import time  # Или другие необходимые импорты

from django.utils import timezone

from moderation.models import Advert


@shared_task
def start_call_task(call_id):
    # Здесь логика инициализации звонка
    # Например, отправка уведомлений, подготовка ресурсов
    print(f"Starting call with ID {call_id}")
    # Можно добавить задержки или проверку статуса
    time.sleep(1)
    # Возвращаем результат или статус
    return f"Call {call_id} started"

@shared_task
def end_call_task(call_id):
    # Логика завершения звонка
    print(f"Ending call with ID {call_id}")
    time.sleep(1)
    return f"Call {call_id} ended"


@shared_task
def check_model_changes():
    """
    Проверяет модели на изменения и при необходимости обновляет их.
    Например, можно обновлять все объявления, у которых есть изменения.
    """
    # Пример: обновлять все объявления, у которых есть изменения за последние 3 часа
    cutoff = timezone.now() - timedelta(hours=3)
    ads_to_update = Advert.objects.filter(updated_at__gte=cutoff)
    for ad in ads_to_update:
        # Тут можно реализовать логику обновления, например, пересчитать какие-то поля
        # или просто обновить поле updated_at
        ad.save()
    # Или логика может быть другой, в зависимости от требований

@shared_task
def update_expired_ads():
    """
    Проверяет объявления, у которых дата обновления прошла, и снимает статус "опубликовано".
    Предположим, есть поле `published` (BooleanField), которое нужно сбросить.
    """
    now = timezone.now()
    # Например, если есть поле `updated_at`, и мы считаем, что объявление устарело
    expired_ads = Advert.objects.filter(updated_at__lte=now - timedelta(hours=5))
    for ad in expired_ads:
        # Предположим, есть поле `published`, которое нужно сбросить
        # Если такого поля нет, добавьте его в модель
        if hasattr(ad, 'published'):
            ad.published = False
            ad.save()
        # Если поле отсутствует, можно реализовать другую логику
