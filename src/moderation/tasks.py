import os
from datetime import timedelta

from celery import shared_task
import time  # Или другие необходимые импорты

from django.utils import timezone



from useraccount.yandex_disk_utils import upload_to_yandex_disk



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


import os
from celery import shared_task
from django.conf import settings
import subprocess
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_model_changes():
    """
    Запускает импорт объявлений из XML файла
    """
    try:
        # Правильный путь к файлу
        script_path = os.path.join(settings.BASE_DIR, '_dump', 'import_adverts_xml.py')

        # Проверяем существует ли файл
        if not os.path.exists(script_path):
            logger.error(f"Файл не найден: {script_path}")
            return f"Ошибка: Файл {script_path} не существует"

        # Меняем рабочую директорию на корень проекта
        project_root = settings.BASE_DIR
        os.chdir(project_root)

        # Запускаем скрипт
        result = subprocess.run(
            ['python3', '_dump/import_adverts_xml.py'],
            capture_output=True,
            text=True,
            timeout=3600  # 1 час таймаут
        )

        if result.returncode == 0:
            logger.info("Импорт выполнен успешно")
            logger.info(f"Вывод: {result.stdout}")
            return f"Успешно: {result.stdout}"
        else:
            logger.error(f"Ошибка импорта: {result.stderr}")
            return f"Ошибка: {result.stderr}"

    except subprocess.TimeoutExpired:
        logger.error("Импорт превысил лимит времени (1 час)")
        return "Ошибка: Таймаут импорта"
    except Exception as e:
        logger.error(f"Ошибка при запуске импорта: {e}")
        return f"Ошибка: {str(e)}"


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

