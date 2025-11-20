import os
from datetime import timedelta

from celery import shared_task
import time  # Или другие необходимые импорты

from django.utils import timezone



from useraccount.yandex_disk_utils import upload_to_yandex_disk

from _dump.import_adverts_xml import URLS


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

from celery import shared_task
from django.core.cache import cache  # Необходимо подключить cache
import logging
import subprocess
import os
from django.conf import settings

logger = logging.getLogger(__name__)

CHECK_MODEL_LOCK_KEY = "check_model_changes_lock"
CHECK_MODEL_LOCK_EXPIRE = 60 * 60 + 60  # 1 час + запас 1 минута

# Общая задача для обработки каждого URL
@shared_task(bind=True, max_retries=3)
def import_advertisements(self, url, batch_size=500):
    """
    Запускает импорт объявлений из XML файла для конкретного URL.
    """
    try:
        script_path = os.path.join(settings.BASE_DIR, "_dump", "import_adverts_xml.py")
        if not os.path.exists(script_path):
            msg = f"Файл не найден: {script_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # Вызываем скрипт импорта для каждого URL
        logger.info(f"Запуск импорта для URL: {url}")
        result = subprocess.run(
            ["python3", script_path, url],  # передаем URL в скрипт
            capture_output=True,
            text=True,
            timeout=3600,  # 1 час таймаут
        )

        if result.returncode == 0:
            logger.info(f"Импорт выполнен успешно для {url}")
            if result.stdout:
                logger.info(f"stdout: {result.stdout[:2000]}")
            return "Импорт выполнен успешно"
        else:
            msg = f"Ошибка импорта для {url} (code={result.returncode}): {result.stderr}"
            logger.error(msg)
            raise RuntimeError(msg)

    except subprocess.TimeoutExpired as e:
        msg = f"Импорт для {url} превысил лимит времени (1 час)"
        logger.error(msg)
        try:
            raise self.retry(exc=e, countdown=600)  # повтор через 10 минут
        except self.MaxRetriesExceededError:
            raise RuntimeError(msg)
    except Exception as e:
        msg = f"Ошибка при запуске импорта для {url}: {e}"
        logger.error(msg)
        try:
            raise self.retry(exc=e, countdown=600)
        except self.MaxRetriesExceededError:
            raise

    return f"Ошибка при импорте {url}"

# Основная задача, которая запускает задачи импорта для всех URL
@shared_task(bind=True, max_retries=3)
def run_import_for_all_urls(self):
    """
    Запускает задачи импорта для всех URL одновременно.
    """
    tasks = []
    for url in URLS:
        # Запуск каждой задачи параллельно
        task = import_advertisements.apply_async(args=[url])
        tasks.append(task)

    # Ждем завершения всех задач
    for task in tasks:
        task.get()

    return "Все задачи импорта завершены."









# Старая таска
# import os
# from celery import shared_task
# from django.conf import settings
# import subprocess
# import logging
# from django.core.cache import cache  # ← нужно подключить cache
#
# logger = logging.getLogger(__name__)
#
# CHECK_MODEL_LOCK_KEY = "check_model_changes_lock"
# CHECK_MODEL_LOCK_EXPIRE = 60 * 60 + 60  # 1 час + запас 1 минута
#
#
# @shared_task(bind=True, max_retries=3)
# def check_model_changes(self):
#     """
#     Запускает импорт объявлений из XML файла.
#     - Не даёт запустить вторую копию, если первая ещё работает (cache-lock).
#     - При таймауте / ошибке — кидаем исключение (Celery помечает как failed / retry).
#     """
#     # ---- БЛОКИРОВКА ----
#     has_lock = cache.add(CHECK_MODEL_LOCK_KEY, "1", CHECK_MODEL_LOCK_EXPIRE)
#     if not has_lock:
#         msg = "Импорт уже запущен, новая задача пропущена"
#         logger.warning(msg)
#         return msg
#
#     try:
#         script_path = os.path.join(settings.BASE_DIR, "_dump", "import_adverts_xml.py")
#
#         if not os.path.exists(script_path):
#             msg = f"Файл не найден: {script_path}"
#             logger.error(msg)
#             # тут лучше бросить ошибку, чтобы увидить в мониторинге
#             raise FileNotFoundError(msg)
#
#         project_root = settings.BASE_DIR
#         os.chdir(project_root)
#
#         logger.info("Запуск импорта объявлений из XML")
#         result = subprocess.run(
#             ["python3", "_dump/import_adverts_xml.py"],
#             capture_output=True,
#             text=True,
#             timeout=3600,  # 1 час таймаут
#         )
#
#         if result.returncode == 0:
#             logger.info("Импорт выполнен успешно")
#             if result.stdout:
#                 logger.info("Импорт stdout: %s", result.stdout[:2000])
#             return "Импорт выполнен успешно"
#
#         else:
#             # Скрипт вернул ненулевой код — считаем это ошибкой
#             msg = f"Ошибка импорта (code={result.returncode}): {result.stderr}"
#             logger.error(msg)
#             # Можно попробовать ретрай
#             raise RuntimeError(msg)
#
#     except subprocess.TimeoutExpired as e:
#         msg = "Импорт превысил лимит времени (1 час)"
#         logger.error(msg)
#         # Можно захотеть ретрай через n секунд
#         try:
#             raise self.retry(exc=e, countdown=600)  # повтор через 10 минут
#         except self.MaxRetriesExceededError:
#             # если ретраев больше нельзя — явно падаем
#             raise RuntimeError(msg)
#
#     except Exception as e:
#         msg = f"Ошибка при запуске импорта: {e}"
#         logger.error(msg)
#         # тоже ретрай
#         try:
#             raise self.retry(exc=e, countdown=600)
#         except self.MaxRetriesExceededError:
#             raise
#
#     finally:
#         # снимаем lock в любом случае
#         cache.delete(CHECK_MODEL_LOCK_KEY)


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

