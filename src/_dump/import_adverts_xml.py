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
import argparse

# Настройки Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_project.settings")
django.setup()

from moderation.models import Advert, CarBrand, CarModel

# === Логирование ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_adverts")


# === Утилиты для парсинга и преобразования данных ===
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


def parse_price(text):
    if not text:
        return None
    norm = str(text).replace(" ", "").replace("\xa0", "").replace(",", ".")
    norm = re.sub(r"[^0-9.]", "", norm)
    try:
        return decimal.Decimal(norm)
    except Exception:
        return None

def parse_engine_volume(text):
    if not text:
        return None
    t = str(text).lower().strip()  # Преобразуем в строку и убираем пробелы

    # Удаляем все символы, кроме цифр, запятой и точки
    t = re.sub(r"[^\d.,]", "", t)

    # Выводим промежуточное значение после фильтрации

    # Проверяем, если строка пуста после очистки
    if not t:
        return None

    # Заменяем запятую на точку, если разделитель десятичной части — запятая
    t = t.replace(",", ".")

    # Выводим окончательную строку перед преобразованием

    try:
        # Преобразуем строку в Decimal
        engine_volume = decimal.Decimal(t)

        # Проверка, что значение укладывается в пределы для max_digits=4, decimal_places=1
        if abs(engine_volume) >= 1000:
            return None

        # Если значение корректно, то округляем до 1 знака после запятой
        return engine_volume.quantize(decimal.Decimal("0.1"))
    except decimal.InvalidOperation as e:
        return None




def parse_power_hp(text):
    if not text:
        return None
    # Оставляем только цифры, удаляя все символы (например, "hk")
    t = re.sub(r"[^\d]", "", str(text))

    # Выводим промежуточное значение после фильтрации

    # Проверяем, если строка пуста после очистки
    if not t:
        return None

    try:
        # Преобразуем строку в целое число
        power = int(t)

        # Проверяем, что мощность больше нуля
        if power <= 0:
            return None

        return power
    except ValueError as e:
        return None

def extract_fields_dict(good_el):
    out = {}
    for f in good_el.findall("./field"):
        name = (f.attrib.get("name") or "").strip()
        value = (f.text or "").strip() if f.text else ""
        out[name] = value
    return out


def extract_images(good_el, limit=7):
    images = []
    for img in good_el.findall("./image"):
        url = (img.text or "").strip()
        if url and is_valid_url(url):
            images.append(url)
            if len(images) >= limit:
                break
    return images


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def map_transmission(text):
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
    if not desc:
        return ""
    desc = re.sub(r"<[^>]+>", " ", str(desc))
    m = re.search(r"(Adresse|Address|Адрес|Asukoht|Lokacija):\s*([A-Za-z0-9\s,.-]+)", desc)
    return m.group(2).strip() if m else ""


# === Основная логика парсинга ===
def good_to_payload(good_el):
    f = extract_fields_dict(good_el)

    name = safe_str(f.get("Название") or f.get("Title") or "Без названия")
    link = safe_str(f.get("URL"))
    if not link or not is_valid_url(link):
        return None

    price = parse_price(f.get("Цена")) or decimal.Decimal(0)
    currency = f.get("Валюта") or "EUR"
    description = f.get("Описание") or f.get("Description") or ""
    address = extract_address_from_description(description)
    images = extract_images(good_el)
    if not images:
        return None

    mileage = parse_int(f.get("Km") or f.get("Przebieg") or f.get("Kilometer") or f.get("Пробег") or f.get("Пробег [км]") or f.get("Najeto")) or 0
    year = parse_int(f.get("Rok produkcji") or f.get("Rok výroby") or f.get("Год выпуска") or f.get("Vyrobeno") or f.get("Год")) or 2000
    power = parse_power_hp(f.get("Leistung") or f.get("Moc")  or f.get("Moc silnika") or f.get("Мощность")  or f.get("Мощност") or f.get("Výkon"))
    engine_volume = parse_engine_volume(f.get("Hubraum") or f.get("Pojemność") or f.get("Pojemność silnika [cm3]") or f.get("Объем") or f.get("Objem"))
    transmission = map_transmission(f.get("Getriebe") or f.get("Skrzynia biegów") or f.get("КПП")  or f.get("Převodovka") or f.get("Převodovka"))
    fuel = map_fuel(f.get("Kraftstoff") or f.get("Rodzaj paliwa") or f.get("Топливо")) or Advert.FuelType.GASOLINE
    drive = map_drive(f.get("Antrieb") or f.get("Napęd") or f.get("Тип привода"))
    doors = parse_int(f.get("Türen") or f.get("Liczba drzwi") or f.get("Дверей") or f.get("Počet dveří")) or 5
    color = safe_str(f.get("Farbe") or f.get("Kolor") or f.get("Цвет") or f.get("Barva"))

    # Создание или поиск марки и модели автомобиля
    car_brand_name = safe_str(f.get("Merke") or f.get("Марка"))
    car_model_name = safe_str(f.get("Modell") or f.get("Модель"))

    car_brand = CarBrand.objects.get_or_create(name=car_brand_name)[0]
    car_model = CarModel.objects.get_or_create(name=car_model_name, brand=car_brand)[0]

    return {
        "name": name[:255],
        "link": link,
        "original_link": link,
        "price": price,
        "currency": currency,
        "description": description,
        "address": address,
        "images": images,
        "mileage": mileage,
        "year": year,
        "power": power,
        "engine_volume": engine_volume,
        "transmission": transmission,
        "fuel": fuel,
        "drive": drive,
        "doors": doors,
        "color": color,
        "car_brand": car_brand,
        "car_model": car_model,
        "updated_at": now(),
    }


def import_from_url(url, batch_size=100):
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
    adverts_to_create = []

    for idx, good in enumerate(goods, start=1):
        try:
            payload = good_to_payload(good)
            if not payload:
                skipped += 1
                continue

            existing_advert = Advert.objects.filter(link=payload['link']).first()
            if existing_advert:
                for field, value in payload.items():
                    setattr(existing_advert, field, value)
                existing_advert.updated_at = now()
                existing_advert.save()
                updated += 1
            else:
                adverts_to_create.append(Advert(**payload))

            if len(adverts_to_create) >= batch_size:
                with transaction.atomic():
                    Advert.objects.bulk_create(adverts_to_create)
                created += len(adverts_to_create)
                adverts_to_create = []

            if idx % 500 == 0:
                logger.info(f"→ обработано {idx} записей...")

        except Exception as e:
            logger.warning(f"[{idx}] Ошибка сохранения ({e.__class__.__name__}): {e}")
            skipped += 1

    if adverts_to_create:
        with transaction.atomic():
            Advert.objects.bulk_create(adverts_to_create)
        created += len(adverts_to_create)

    logger.info(f"Готово ✅ Создано: {created}, Обновлено: {updated}, Пропущено: {skipped}")


# === Запуск с аргументом командной строки ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Запуск импорта для указанной ссылки')
    parser.add_argument('--url', type=str, help='URL для импорта')
    args = parser.parse_args()

    if args.url:
        import_from_url(args.url)  # Обрабатываем только указанную ссылку
    else:
        for url in URLS:
            import_from_url(url)  # Обрабатываем все ссылки из списка
