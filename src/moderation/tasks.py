from celery import shared_task
import time
from useraccount.yandex_disk_utils import upload_to_yandex_disk
import os
from celery import shared_task
from django.conf import settings
import subprocess
import logging
from django.core.cache import cache
from celery import shared_task
import logging
import subprocess
import os
from django.core.cache import cache
from django.conf import settings

# Логирование
logger = logging.getLogger(__name__)

CHECK_MODEL_LOCK_KEY = "check_model_changes_lock"
CHECK_MODEL_LOCK_EXPIRE = 60 * 60 + 60  # 1 час + запас 1 минута
from celery import shared_task, group
import subprocess
import os
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

CHECK_MODEL_LOCK_KEY = "check_model_changes_lock"
CHECK_MODEL_LOCK_EXPIRE = 60 * 60 + 60  # 1 час + запас 1 минута

@shared_task(bind=True, max_retries=3)
def check_model_changes(self):
    """
    Запускает импорт объявлений из XML файла для каждого URL из списка URLS.
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
        # Источник данных
        URLS = [
            "https://s3.q-parser.ru/automata/63e72f72e46ff8/finn.no.xml",
            "https://s3.q-parser.ru/automata/63e700c07fab20/gratka.pl.xml",
            "https://s3.q-parser.ru/automata/63e72c68f795dc/sauto.cz.xml",
            "https://s3.q-parser.ru/automata/63e72a4694fc7c/mobile.bg.xml",
            "https://s3.q-parser.ru/automata/63e72bf469855c/tipcars.com.xml",
            "https://s3.q-parser.ru/automata/63e72af857b188/bestauto.ro.xml",
            "https://s3.q-parser.ru/automata/63e72a09b6ef48/webauto.de.xml",
            "https://s3.q-parser.ru/automata/63e72d2b212094/auto24.ee.xml",
            "https://s3.q-parser.ru/automata/63e70467af7a58/autotrader.pl.xml",
            "https://s3.q-parser.ru/automata/63e72b7a4ff0a0/car24.bg.xml",
            "https://s3.q-parser.ru/automata/63e72acaa3f4f0/auto.ro.xml",
            "https://s3.q-parser.ru/automata/63e72a6be8bfa8/yauto.cz.xml",
            "https://s3.q-parser.ru/automata/63e704d25ef57c/autovit.ro.xml",
            "https://s3.q-parser.ru/automata/63e72d86e3a604/otomoto.pl.xml",
            "https://s3.q-parser.ru/automata/63e72b3724b54c/cars.cz.xml"
        ]

        script_path = os.path.join(settings.BASE_DIR, "_dump", "import_adverts_xml.py")

        if not os.path.exists(script_path):
            msg = f"Файл не найден: {script_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        project_root = settings.BASE_DIR
        os.chdir(project_root)

        logger.info("Запуск импорта объявлений из XML")

        # Запуск для каждого URL в параллельных задачах
        tasks = []
        for url in URLS:
            logger.info(f"Обработка URL: {url}")
            tasks.append(import_adverts_from_url.s(url))  # Отправляем URL как аргумент

        # Группируем все задачи и запускаем
        group(tasks)()

        return "Импорт для всех URL начат успешно"

    except Exception as e:
        msg = f"Ошибка при запуске импорта: {e}"
        logger.error(msg)
        try:
            raise self.retry(exc=e, countdown=600)
        except self.MaxRetriesExceededError:
            raise

    finally:
        # снимаем lock в любом случае
        cache.delete(CHECK_MODEL_LOCK_KEY)


@shared_task
def import_adverts_from_url(url):
    """
    Импортирует данные с одного URL.
    """
    script_path = os.path.join(settings.BASE_DIR, "_dump", "import_adverts_xml.py")

    if not os.path.exists(script_path):
        msg = f"Файл не найден: {script_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    project_root = settings.BASE_DIR
    os.chdir(project_root)

    logger.info(f"Запуск импорта для URL: {url}")

    try:
        result = subprocess.run(
            ["python3", "_dump/import_adverts_xml.py", "--url", url],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 час таймаут
        )

        if result.returncode == 0:
            logger.info(f"Импорт для {url} выполнен успешно")
            if result.stdout:
                logger.info("Импорт stdout: %s", result.stdout[:2000])
        else:
            msg = f"Ошибка импорта для {url} (code={result.returncode}): {result.stderr}"
            logger.error(msg)
            raise RuntimeError(msg)

    except subprocess.TimeoutExpired as e:
        msg = f"Импорт для {url} превысил лимит времени (1 час)"
        logger.error(msg)
        raise self.retry(exc=e, countdown=600)  # повтор через 10 минут

    except Exception as e:
        msg = f"Ошибка при импорте {url}: {e}"
        logger.error(msg)
        raise self.retry(exc=e, countdown=600)  # повтор через 10 минут





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

