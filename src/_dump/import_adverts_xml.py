import os
import sys
import re
import io
import decimal
import logging
import requests
from urllib.parse import urlparse
import django
from lxml import etree as ET  # ✅ быстрее xml.etree

# Настройки Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_project.settings")

# Функции импорта без вызова django.setup() здесь
from moderation.models import Advert  # Важно! Импортировать Django модели после настройки Django

# === Логирование ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_adverts")

# === Источники ===
URLS = [
    "https://s3.q-parser.ru/automata/63e72f72e46ff8/finn.no.xml",
    "https://s3.q-parser.ru/automata/63e700c07fab20/gratka.pl.xml",
    "https://s3.q-parser.ru/automata/63e72c68f795dc/sauto.cz.xml",
    # Добавьте сюда остальные URL
]

# === Утилиты ===
def safe_str(x):
    return str(x).strip() if x else ""

def parse_int(text):
    if not text:
        return None
    try:
        digits = re.sub(r"[^\d]", "", str(text))
        return int(digits) if digits else None
    except Exception:
        return None

# Ваша логика импорта...

def import_from_url(url, batch_size=500):
    logger.info(f"Скачиваю: {url}")
    try:
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        return

    try:
        root = ET.parse(io.BytesIO(resp.content)).getroot()
    except Exception as e:
        logger.error(f"Ошибка парсинга XML: {e}")
        return

    goods = root.findall(".//good")
    logger.info(f"Найдено {len(goods)} объявлений")

    created = updated = skipped = 0
    buffer = []

    for idx, good in enumerate(goods, start=1):
        try:
            payload = good_to_payload(good)
            if not payload:
                print(payload)
                skipped += 1
                continue

            obj, is_created = Advert.objects.update_or_create(
                link=payload["link"], defaults=payload
            )
            if is_created:
                created += 1
            else:
                updated += 1

            if idx % 500 == 0:
                logger.info(f"→ обработано {idx} записей...")
        except Exception as e:
            logger.warning(f"[{idx}] Ошибка сохранения ({e.__class__.__name__}): {e}")
            skipped += 1

    logger.info(f"Готово ✅ Создано: {created}, Обновлено: {updated}, Пропущено: {skipped}")

# === Запуск ===
if __name__ == "__main__":
    # Оставляем вызов для одного URL для теста, но он будет работать через Celery
    url = "https://s3.q-parser.ru/automata/63e72f72e46ff8/finn.no.xml"
    import_from_url(url)
