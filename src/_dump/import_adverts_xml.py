# запускается так
# python3 _dump/import_adverts_xml.py --url "https://s3.q-parser.ru/automata/63e72f72e46ff8/finn.no.xml"
import os
import sys
import re
import io
import decimal
import logging
import requests
from urllib.parse import urlparse

import django
from django.db import transaction
from django.utils.timezone import now
from lxml import etree as ET  # ✅ быстрее xml.etree

# Настройки Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_project.settings")
django.setup()

from moderation.models import Advert

# === Логирование ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_adverts")

# === Источники XML-фидов ===
URLS = [
    "https://s3.q-parser.ru/automata/63e72f72e46ff8/finn.no.xml",  # Норвегия
    "https://s3.q-parser.ru/automata/63e700c07fab20/gratka.pl.xml",  # Польша
    "https://s3.q-parser.ru/automata/63e72c68f795dc/sauto.cz.xml",  # Чехия
    "https://s3.q-parser.ru/automata/63e72a4694fc7c/mobile.bg.xml",  # Болгария
    "https://s3.q-parser.ru/automata/63e72bf469855c/tipcars.com.xml",  # Международный
    "https://s3.q-parser.ru/automata/63e72af857b188/bestauto.ro.xml",  # Румыния
    "https://s3.q-parser.ru/automata/63e72a09b6ef48/webauto.de.xml",  # Германия
    "https://s3.q-parser.ru/automata/63e72d2b212094/auto24.ee.xml",  # Эстония
    "https://s3.q-parser.ru/automata/63e70467af7a58/autotrader.pl.xml",  # Польша
    "https://s3.q-parser.ru/automata/63e72b7a4ff0a0/car24.bg.xml",  # Болгария
    "https://s3.q-parser.ru/automata/63e72acaa3f4f0/auto.ro.xml",  # Румыния
    "https://s3.q-parser.ru/automata/63e72a6be8bfa8/yauto.cz.xml",  # Чехия
    "https://s3.q-parser.ru/automata/63e704d25ef57c/autovit.ro.xml",  # Румыния
    "https://s3.q-parser.ru/automata/63e72d86e3a604/otomoto.pl.xml",  # Польша
    "https://s3.q-parser.ru/automata/63e72b3724b54c/cars.cz.xml"  # Чехия
]


# === Утилиты для парсинга и преобразования данных ===

def safe_str(x):
    """Безопасное преобразование в строку с удалением пробелов"""
    return str(x).strip() if x else ""


def parse_int(text):
    """Парсит целое число, удаляя все нецифровые символы"""
    if not text:
        return None
    try:
        digits = re.sub(r"[^\d]", "", str(text))
        return int(digits) if digits else None
    except Exception:
        return None


def parse_price(text):
    """Парсит цену, удаляя пробелы и преобразуя запятые в точки"""
    if not text:
        return None
    norm = str(text).replace(" ", "").replace("\xa0", "").replace(",", ".")
    norm = re.sub(r"[^0-9.]", "", norm)
    try:
        return decimal.Decimal(norm)
    except Exception:
        return None


def parse_engine_volume(text):
    """Парсит объем двигателя: '2393 ccm' -> 2.4 ; '2,0 L' -> 2.0"""
    if not text:
        return None
    t = str(text).lower()
    try:
        if "ccm" in t:
            raw = re.findall(r"[\d.,]+", t)[0].replace(",", ".")
            liters = decimal.Decimal(raw) / 1000
            return liters.quantize(decimal.Decimal("0.1"))
        if "l" in t:
            raw = re.findall(r"[\d.,]+", t)[0].replace(",", ".")
            return decimal.Decimal(raw).quantize(decimal.Decimal("0.1"))
    except Exception:
        return None
    return None


def parse_power_hp(text):
    """Парсит мощность в л.с.: '150 PS' -> 150, '110 kW' -> 150 (конвертация)"""
    if not text:
        return None
    t = str(text).lower()
    try:
        if "ps" in t:
            return int(re.findall(r"(\d+)\s*ps", t)[0])
        if "kw" in t:
            kw = int(re.findall(r"(\d+)\s*kw", t)[0])
            return int(round(kw * 1.35962))  # Конвертация kW в HP
    except Exception:
        return None
    return None


def extract_fields_dict(good_el):
    """Извлекает все поля из XML элемента <good> в словарь"""
    out = {}
    for f in good_el.findall("./field"):
        name = (f.attrib.get("name") or "").strip()
        value = (f.text or "").strip() if f.text else ""
        out[name] = value
    return out


def extract_images(good_el, limit=7):
    """Извлекает URL изображений из элемента <good> (максимум limit штук)"""
    images = []
    for img in good_el.findall("./image"):
        url = (img.text or "").strip()
        if url and is_valid_url(url):
            images.append(url)
            if len(images) >= limit:
                break
    return images


def is_valid_url(url):
    """Проверяет валидность URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def map_transmission(text):
    """Маппит текст типа КПП на enum значения Advert.TransmissionType"""
    if not text:
        return None
    t = text.lower()
    if any(x in t for x in ["manual", "schalt", "manuell", "ręczna", "mechan"]):
        return Advert.TransmissionType.MANUAL
    if any(x in t for x in ["auto", "automatik", "automat", "automatyczna"]):
        return Advert.TransmissionType.AUTOMATIC
    if "cvt" in t:
        return Advert.TransmissionType.CVT
    if any(x in t for x in ["robot", "dsg"]):
        return Advert.TransmissionType.ROBOT
    return None


def map_fuel(text):
    """Маппит текст типа топлива на enum значения Advert.FuelType"""
    if not text:
        return None
    t = text.lower()
    if any(k in t for k in ["diesel", "nafta", "дизел"]):
        return Advert.FuelType.DIESEL
    if any(k in t for k in ["benzin", "gasoline", "petrol", "benzyna", "бензин"]):
        return Advert.FuelType.GASOLINE
    if any(k in t for k in ["hybrid", "hibrid", "хибрид"]):
        return Advert.FuelType.HYBRID
    if any(k in t for k in ["elekt", "electric", "електри"]):
        return Advert.FuelType.ELECTRIC
    if any(k in t for k in ["gaz", "lpg", "cng", "газ"]):
        return getattr(Advert.FuelType, "GAS", Advert.FuelType.GASOLINE)
    return None


def map_drive(text):
    """Маппит текст типа привода на enum значения Advert.DriveType"""
    if not text:
        return None
    t = text.lower()
    if any(k in t for k in ["awd", "4x4", "4wd", "quattro", "allrad"]):
        return Advert.DriveType.AWD
    if any(k in t for k in ["fwd", "front", "vorder", "przedni", "передний"]):
        return Advert.DriveType.FWD
    if any(k in t for k in ["rwd", "heck", "hinter", "tylny", "задний"]):
        return Advert.DriveType.RWD
    return None


def extract_address_from_description(desc):
    """Извлекает адрес из описания по ключевым словам"""
    if not desc:
        return ""
    desc = re.sub(r"<[^>]+>", " ", str(desc))
    m = re.search(r"(Adresse|Address|Адрес|Asukoht|Lokacija):\s*([A-Za-z0-9\s,.-]+)", desc)
    return m.group(2).strip() if m else ""


# === Основная логика парсинга ===

def good_to_payload(good_el):
    """
    Преобразует XML элемент <good> в словарь для сохранения в модель Advert

    Используемые поля из XML для парсинга:
    - Название/Title: название автомобиля
    - URL: ссылка на оригинальное объявление
    - Цена: стоимость автомобиля
    - Валюта: валюта цены
    - Описание/Description: полное описание
    - Km/Przebieg/Kilometer: пробег
    - Rok produkcji/Rok výroby/Год: год выпуска
    - Leistung/Moc: мощность
    - Hubraum/Pojemność: объем двигателя
    - Getriebe/Skrzynia biegów: тип КПП
    - Kraftstoff/Rodzaj paliwa: тип топлива
    - Antrieb/Napęd: тип привода
    - Türen/Liczba drzwi: количество дверей
    - Farbe/Kolor: цвет

    Также извлекаются изображения из тегов <image>
    """
    # Извлекаем все поля из XML в словарь
    f = extract_fields_dict(good_el)

    # === ОБЯЗАТЕЛЬНЫЕ ПОЛЯ ===
    # Название автомобиля - используется для поля 'name'
    name = safe_str(f.get("Название") or f.get("Title") or "Без названия")

    # Ссылка на оригинальное объявление - используется как уникальный идентификатор
    link = safe_str(f.get("URL"))
    if not link or not is_valid_url(link):
        return None

    # === ЦЕНА И ВАЛЮТА ===
    # Цена автомобиля - используется для поля 'price'
    price = parse_price(f.get("Цена")) or decimal.Decimal(0)
    # Валюта цены - используется для поля 'currency'
    currency = f.get("Валюта") or "EUR"

    # === ОПИСАНИЕ И АДРЕС ===
    # Полное описание автомобиля - используется для поля 'description'
    description = f.get("Описание") or f.get("Description") or ""
    # Адрес из описания - используется для поля 'address'
    address = extract_address_from_description(description)

    # === ИЗОБРАЖЕНИЯ ===
    # Список URL изображений - используется для поля 'images'
    images = extract_images(good_el)
    if not images:
        return None  # хотя бы 1 фото обязательно

    # === ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ ===
    # Пробег - используется для поля 'mileage'
    mileage = parse_int(f.get("Km") or f.get("Przebieg") or f.get("Kilometer") or f.get("Пробег")) or 0

    # Год выпуска - используется для поля 'year'
    year = parse_int(f.get("Rok produkcji") or f.get("Rok výroby") or f.get("Год выпуска") or f.get("Год")) or 2000

    # Мощность в л.с. - используется для поля 'power'
    power = parse_power_hp(f.get("Leistung") or f.get("Moc") or f.get("Мощность"))

    # Объем двигателя в литрах - используется для поля 'engine_volume'
    engine_volume = parse_engine_volume(f.get("Hubraum") or f.get("Pojemność") or f.get("Объем"))

    # Тип КПП - используется для поля 'transmission'
    transmission = map_transmission(f.get("Getriebe") or f.get("Skrzynia biegów") or f.get("КПП"))

    # Тип топлива - используется для поля 'fuel'
    fuel = map_fuel(f.get("Kraftstoff") or f.get("Rodzaj paliwa") or f.get("Топливо")) or Advert.FuelType.GASOLINE

    # Тип привода - используется для поля 'drive'
    drive = map_drive(f.get("Antrieb") or f.get("Napęd") or f.get("Тип привода"))

    # Количество дверей - используется для поля 'doors'
    doors = parse_int(f.get("Türen") or f.get("Liczba drzwi")or f.get("Дверей")) or 5

    # Цвет - используется для поля 'color'
    color = safe_str(f.get("Farbe") or f.get("Kolor") or f.get("Цвет"))

    # === ФОРМИРУЕМ РЕЗУЛЬТИРУЮЩИЙ СЛОВАРЬ ===
    return {
        "name": name[:255],  # Название автомобиля (макс 255 символов)
        "link": link,  # Ссылка на оригинальное объявление
        "original_link": link,  # Дублирование ссылки
        "price": price,  # Цена
        "currency": currency,  # Валюта (EUR по умолчанию)
        "description": description,  # Полное описание
        "address": address,  # Адрес
        "images": images,  # Список URL изображений
        "mileage": mileage,  # Пробег
        "year": year,  # Год выпуска
        "power": power,  # Мощность в л.с.
        "engine_volume": engine_volume,  # Объем двигателя в литрах
        "transmission": transmission,  # Тип КПП
        "fuel": fuel,  # Тип топлива
        "drive": drive,  # Тип привода
        "doors": doors,  # Количество дверей
        "color": color,  # Цвет
        "updated_at": now(),  # Время обновления
    }


def import_from_url(url, batch_size=500):
    """
    Основная функция импорта данных из XML URL
    """
    logger.info(f"Скачиваю: {url}")
    try:
        # Скачиваем XML файл
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        return

    try:
        # Парсим XML
        root = ET.parse(io.BytesIO(resp.content)).getroot()
    except Exception as e:
        logger.error(f"Ошибка парсинга XML: {e}")
        return

    # Находим все элементы <good> в XML
    goods = root.findall(".//good")
    logger.info(f"Найдено {len(goods)} объявлений")

    created = updated = skipped = 0

    # Обрабатываем каждое объявление
    for idx, good in enumerate(goods, start=1):
        try:
            # Преобразуем XML в словарь для модели
            payload = good_to_payload(good)
            if not payload:
                skipped += 1
                continue

            # Создаем или обновляем запись в базе данных
            # Используем поле 'link' как уникальный идентификатор
            obj, is_created = Advert.objects.update_or_create(
                link=payload["link"], defaults=payload
            )
            if is_created:
                created += 1
            else:
                updated += 1

            # Логируем прогресс каждые 500 записей
            if idx % 500 == 0:
                logger.info(f"→ обработано {idx} записей...")
        except Exception as e:
            logger.warning(f"[{idx}] Ошибка сохранения ({e.__class__.__name__}): {e}")
            skipped += 1

    # Финальная статистика
    logger.info(f"Готово ✅ Создано: {created}, Обновлено: {updated}, Пропущено: {skipped}")


# === Запуск скрипта ===
if __name__ == "__main__":
    # Обрабатываем все URL из списка
    for i, url in enumerate(URLS, 1):
        logger.info(f"--- [{i}/{len(URLS)}] {url}")
        import_from_url(url)