import logging
from datetime import time

import requests
from celery import shared_task
from django.core.cache import cache
from _dump.import_adverts_xml import import_from_url
import logging
from celery import shared_task
from django.core.cache import cache
from _dump.import_adverts_xml import import_from_url  # Переносим импорт сюда
import logging
from celery import shared_task
from django.core.cache import cache
from django.apps import apps  # Для динамического импорта моделей

logger = logging.getLogger(__name__)

CHECK_MODEL_LOCK_KEY = "check_model_changes_lock"
CHECK_MODEL_LOCK_EXPIRE = 60 * 60 + 60  # 1 час + запас 1 минута


@shared_task(bind=True, max_retries=3)
def check_model_changes(self):
    """
    Запускает импорт объявлений из XML файла.
    - Не даёт запустить вторую копию, если первая ещё работает (cache-lock).
    - При таймауте / ошибке — кидаем исключение (Celery помечает как failed / retry).
    """
    # ---- БЛОКИРОВКА ----
    has_lock = cache.add(CHECK_MODEL_LOCK_KEY, "1", CHECK_MODEL_LOCK_EXPIRE)
    if not has_lock:
        msg = "Импорт уже запущен, новая задача пропущена"
        logger.warning(msg)
        return msg

    try:
        # Запуск импорта для каждой ссылки как отдельная задача
        for url in URLS:
            logger.info(f"Запуск задачи для {url}")
            import_from_url_task.apply_async(args=[url])  # Запускаем задачу для каждой ссылки в очередь
        return "Все задачи успешно запущены"

    except Exception as e:
        msg = f"Ошибка при запуске импорта: {e}"
        logger.error(msg)
        raise


@shared_task(bind=True, max_retries=3)
def import_from_url_task(self, url):
    """
    Эта задача выполняет импорт объявлений из URL
    """
    logger.info(f"Запуск импорта для: {url}")
    try:
        from _dump.import_adverts_xml import import_from_url  # Переместили импорт сюда
        import_from_url(url)
        logger.info(f"Импорт завершен для: {url}")
    except Exception as e:
        logger.error(f"Ошибка импорта для {url}: {str(e)}")
        raise self.retry(exc=e, countdown=60)  # Повтор через 60 секунд в случае ошибки





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
def delete_old_ads():
    """
    Простая задача для удаления старых объявлений
    """
    from moderation.models import Advert

    deleted_count = Advert.objects.delete_old_ads(hours_threshold=5)
    return f"Удалено {deleted_count} старых объявлений"


@shared_task(bind=True, max_retries=3)
def upload_to_drive_and_delete(self, record_id):
    """
    Задача для загрузки файла на Яндекс.Диск и удаления записи
    """
    try:
        from useraccount.models import Record

        record = Record.objects.get(id=record_id)
        record.uploaded = True
        record.save()

        # Проверяем существование файла
        if not record.audio or not os.path.exists(record.audio.path):
            print(f"Файл не существует: {record.audio.path}")
            record.delete()
            return f"Файл не существует, запись {record_id} удалена"
        # Загружаем на Яндекс.Диск
        success = upload_to_yandex_disk(
            file_path=record.audio.path,
            file_name=os.path.basename(record.audio.path),
            folder_path='audio_records'  # Папка на Яндекс.Диске
        )
        if success:
            # Удаляем физический файл
            if os.path.exists(record.audio.path):
                os.remove(record.audio.path)
                print(f"Локальный файл удален: {record.audio.path}")

            # Удаляем запись из базы
            record.delete()

            return f"Файл загружен на Яндекс.Диск и запись {record_id} удалена"


    except Record.DoesNotExist:
        return f"Запись {record_id} не найдена"
    except Exception as e:
        print(f"Ошибка в задаче: {e}")
        raise self.retry(exc=e)

