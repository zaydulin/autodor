import os
import django
import sys
import io
import re
import decimal
import requests
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_project.settings")
django.setup()

# === Список ссылок на XML ===
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

from moderation.models import Advert


# === Утилиты ===
def parse_int(text):
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse_price(text):
    if not text:
        return None
    norm = text.replace(" ", "").replace("\xa0", "").replace(",", ".")
    norm = re.sub(r"[^0-9.]", "", norm)
    if not norm:
        return None
    try:
        return decimal.Decimal(norm)
    except:
        return None


def extract_fields_dict(good_el):
    out = {}
    for f in good_el.findall("./field"):
        name = (f.attrib.get("name") or "").strip()
        value = (f.text or "").strip()
        out[name] = value
    return out


def extract_images(good_el, limit=7):
    images = []
    for img in good_el.findall("./image"):
        url = (img.text or "").strip()
        if url and is_valid_url(url):
            images.append(url)
            if limit and len(images) >= limit:
                break
    return images


def is_valid_url(url):
    """Проверяет, является ли строка валидным URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def parse_engine_volume(text):
    """ '2393 ccm' -> 2.4 ; '2,0 L' -> 2.0 """
    if not text:
        return None
    m = re.search(r"(\d[\d\.,]*)\s*ccm", text, flags=re.I)
    if m:
        raw = m.group(1).replace(".", "").replace(",", ".")
        try:
            liters = decimal.Decimal(raw) / decimal.Decimal(1000)
            return liters.quantize(decimal.Decimal("0.1"))
        except:
            pass
    m2 = re.search(r"(\d+(?:[\.,]\d+)?)\s*[lL]", text)
    if m2:
        try:
            return decimal.Decimal(m2.group(1).replace(",", ".")).quantize(decimal.Decimal("0.1"))
        except:
            pass
    return None


def parse_power_hp(text):
    # "125kW (170 PS)" -> 170
    if not text:
        return None
    m = re.search(r"\((\d+)\s*PS\)", text, flags=re.I)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d+)\s*kW", text, flags=re.I)
    if m2:
        try:
            kw = int(m2.group(1))
            return int(round(kw * 1.35962))
        except:
            return None
    return None


def map_transmission(text):
    if not text:
        return None
    t = text.strip().lower()
    if "schalt" in t or "mechan" in t or "manuell" in t or "ręczna" in t:
        return Advert.TransmissionType.MANUAL
    if "automatik" in t or "automatic" in t or "automat" in t or "automatyczna" in t:
        return Advert.TransmissionType.AUTOMATIC
    if "cvt" in t:
        return Advert.TransmissionType.CVT
    if "robot" in t or "dsg" in t:
        return Advert.TransmissionType.ROBOT
    return None


def map_fuel(text):
    if not text:
        return None
    t = text.strip().lower()
    if "diesel" in t or "nafta" in t or "дизел" in t:
        return Advert.FuelType.DIESEL
    if "benzin" in t or "gasoline" in t or "petrol" in t or "benzyna" in t or "бензин" in t:
        return Advert.FuelType.GASOLINE
    if "hybrid" in t or "hibrid" in t or "хибрид" in t:
        return Advert.FuelType.HYBRID
    if "elekt" in t or "electric" in t or "електри" in t:
        return Advert.FuelType.ELECTRIC
    if "gaz" in t or "lpg" in t or "cng" in t or "газ" in t:
        return Advert.FuelType.GAS
    return None


def map_drive(text):
    if not text:
        return None
    t = text.strip().lower()
    if "allrad" in t or "quattro" in t or "awd" in t or "4x4" in t or "4wd" in t:
        return Advert.DriveType.AWD
    if "vorder" in t or "front" in t or "fwd" in t or "przedni" in t or "передний" in t:
        return Advert.DriveType.FWD
    if "hinter" in t or "heck" in t or "rwd" in t or "tylny" in t or "задний" in t:
        return Advert.DriveType.RWD
    return None


def extract_address_from_description(description):
    """Извлекает адрес из описания"""
    if not description or not isinstance(description, str):
        return ''

    # Паттерны для поиска адреса в разных форматах
    patterns = [
        r'Anschrift:\s*<\/td>\s*<td>([\s\S]*?)<\/td>',
        r'Adresse:\s*([^<]+)',
        r'Address:\s*([^<]+)',
        r'Адрес:\s*([^<]+)',
        r'Asukoht:\s*([^<]+)',
        r'Lokacija:\s*([^<]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            address = match.group(1)
            # Очистка от HTML тегов
            address = re.sub(r'<[^>]+>', ' ', address)
            address = re.sub(r'\s+', ' ', address).strip()
            return address

    return ''


def good_to_payload(good_el, images_limit=7, is_first_url=False):
    fields = extract_fields_dict(good_el)
    images = extract_images(good_el, images_limit)

    name = fields.get("Название")
    link = fields.get("URL")
    price = parse_price(fields.get("Цена"))
    currency = fields.get("Валюта")

    if not name or not link or price is None or not currency:
        logger.warning(f"Пропущено объявление из-за отсутствия обязательных полей: {name}")
        return None

    description = fields.get("Описание") or fields.get("Description") or fields.get("Opis") or ""
    address = extract_address_from_description(description)

    # Извлекаем дополнительные поля для разных сайтов
    mileage = (parse_int(fields.get("Kilometer")) or
               parse_int(fields.get("Kilometerstand")) or
               parse_int(fields.get("Priebeg")) or
               parse_int(fields.get("Przebieg")) or
               parse_int(fields.get("Tachometr")) or
               parse_int(fields.get("Km")))

    year = (parse_int(fields.get("Erstzulassung")) or
            parse_int(fields.get("Modellår")) or
            parse_int(fields.get("Година на производство")) or
            parse_int(fields.get("Rok produkcji")) or
            parse_int(fields.get("Rok výroby")))

    power = (parse_power_hp(fields.get("Leistung")) or
             parse_power_hp(fields.get("Effekt")) or
             parse_power_hp(fields.get("Moc")) or
             parse_power_hp(fields.get("Putere")) or
             parse_power_hp(fields.get("Мощност")))

    engine_volume = (parse_engine_volume(fields.get("Hubraum")) or
                     parse_engine_volume(fields.get("Slagvolum")) or
                     parse_engine_volume(fields.get("Pojemność")) or
                     parse_engine_volume(fields.get("Capacitate cilindrica")) or
                     parse_engine_volume(fields.get("Кубатура")))

    transmission = (map_transmission(fields.get("Getriebe")) or
                    map_transmission(fields.get("Girkasse")) or
                    map_transmission(fields.get("Skrzynia biegów")) or
                    map_transmission(fields.get("Cutie de viteze")))

    fuel = (map_fuel(fields.get("Kraftstoff")) or
            map_fuel(fields.get("Drivstoff")) or
            map_fuel(fields.get("Rodzaj paliwa")) or
            map_fuel(fields.get("Combustibil")) or
            map_fuel(fields.get("Двигател")))

    drive = (map_drive(fields.get("Antrieb")) or
             map_drive(fields.get("Hjuldrift")) or
             map_drive(fields.get("Napęd")) or
             map_drive(fields.get("Transmisie")))

    if not fuel or not images or mileage or not engine_volume or not transmission or not drive:
        return None

    payload = {
        "name": name,
        "link": link,
        "original_link": link,
        "address": address,
        "price": price,
        "currency": currency,
        "description": description,
        "images": images,
        "subtitle": fields.get("Подзаголовок"),
        "article": fields.get("Артикул"),
        "mileage": mileage,
        "color": fields.get("Farbe") or fields.get("Kolor") or fields.get("Farge") or fields.get("Culoare"),
        "doors": parse_int(fields.get("Türen")) or parse_int(fields.get("Dører")) or parse_int(
            fields.get("Liczba drzwi")),
        "power": power,
        "engine_volume": engine_volume,
        "year": year,
        "transmission": transmission,
        "fuel": fuel,
        "drive": drive,
    }

    # Если это первая ссылка — парсим brand и model_auto
    if is_first_url and name:
        parts = name.split(maxsplit=1)
        payload["brand"] = parts[0]
        payload["model_auto"] = parts[1] if len(parts) > 1 else ""

    return payload


def import_from_url(url, update_by="article", is_first_url=False):
    logger.info(f"\nСкачиваю: {url}")
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        return

    try:
        root = ET.parse(io.BytesIO(resp.content)).getroot()
    except Exception as e:
        logger.error(f"Ошибка парсинга XML: {e}")
        return

    goods = root.findall("./good")
    logger.info(f"Найдено {len(goods)} объявлений")

    created = updated = skipped = 0
    for idx, good in enumerate(goods, start=1):
        try:
            payload = good_to_payload(good, is_first_url=is_first_url)
            if not payload:
                skipped += 1
                continue

            # Проверяем наличие изображений
            if not payload.get("images"):
                skipped += 1
                continue

            if update_by == "article" and payload.get("article"):
                obj, is_created = Advert.objects.update_or_create(
                    article=payload["article"], defaults=payload
                )
            elif update_by == "link" and payload.get("link"):
                obj, is_created = Advert.objects.update_or_create(
                    link=payload["link"], defaults=payload
                )
            else:
                obj = Advert.objects.create(**payload)
                is_created = True

            if is_created:
                created += 1
            else:
                updated += 1

        except Exception as e:
            logger.error(f"[{idx}] Ошибка сохранения: {e}")
            skipped += 1
            continue

    logger.info(f"Готово. Создано: {created}, обновлено: {updated}, пропущено: {skipped}")


# === Запуск для всех ссылок ===
if __name__ == "__main__":
    for i, url in enumerate(URLS):
        logger.info(f"Обработка URL {i + 1}/{len(URLS)}: {url}")
        import_from_url(url, is_first_url=(i == 0))