import os
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
    os.system('python3 /var/www/autodor/src/_dump/import_adverts_xml.py')
