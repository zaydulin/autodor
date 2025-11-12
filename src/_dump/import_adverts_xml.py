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

# === Источники ===
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

# === Утилиты ===
RE_INT = re.compile(r"\d+")
RE_FLOAT = re.compile(r"[\d\.,]+")


def parse_int(text):
    if not text:
        return None
    m = RE_INT.findall(text)
    return int("".join(m)) if m else None


def parse_price(text):
    if not text:
        return None
    norm = re.sub(r"[^\d.,]", "", text.replace(" ", "").replace("\xa0", ""))
    norm = norm.replace(",", ".")
    try:
        return decimal.Decimal(norm)
    except decimal.InvalidOperation:
        return None


def parse_engine_volume(text):
    if not text:
        return None
    t = text.lower()
    if "ccm" in t:
        val = RE_FLOAT.search(t)
        if val:
            liters = decimal.Decimal(val.group(0).replace(",", ".")) / 1000
            return liters.quantize(decimal.Decimal("0.1"))
    if "l" in t:
        val = RE_FLOAT.search(t)
        if val:
            return decimal.Decimal(val.group(0).replace(",", ".")).quantize(decimal.Decimal("0.1"))
    return None


def parse_power_hp(text):
    if not text:
        return None
    text = text.lower()
    if "ps" in text:
        m = re.search(r"(\d+)\s*ps", text)
        if m:
            return int(m.group(1))
    if "kw" in text:
        m = re.search(r"(\d+)\s*kw", text)
        if m:
            return int(round(int(m.group(1)) * 1.35962))
    return None


def is_valid_url(url):
    try:
        u = urlparse(url)
        return all([u.scheme, u.netloc])
    except Exception:
        return False


def extract_fields_dict(good_el):
    return {f.get("name", "").strip(): (f.text or "").strip() for f in good_el.findall("field")}


def extract_images(good_el, limit=7):
    urls = [img.text.strip() for img in good_el.findall("image") if img.text and is_valid_url(img.text)]
    return urls[:limit]


def extract_address_from_description(description: str) -> str:
    if not description:
        return ""
    for pattern in [
        r"Adresse:\s*([^<]+)",
        r"Address:\s*([^<]+)",
        r"Адрес:\s*([^<]+)",
        r"Asukoht:\s*([^<]+)",
        r"Lokacija:\s*([^<]+)",
    ]:
        m = re.search(pattern, description, flags=re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1).strip())
    return ""


# === Маппинг ===
def map_transmission(t):
    if not t:
        return None
    t = t.lower()
    if any(k in t for k in ["manual", "schalt", "manuell", "ręczna", "mechan"]):
        return Advert.TransmissionType.MANUAL
    if any(k in t for k in ["auto", "automatik", "automat", "automatyczna"]):
        return Advert.TransmissionType.AUTOMATIC
    if "cvt" in t:
        return Advert.TransmissionType.CVT
    if any(k in t for k in ["robot", "dsg"]):
        return Advert.TransmissionType.ROBOT
    return None


def map_fuel(t):
    if not t:
        return None
    t = t.lower()
    if any(k in t for k in ["diesel", "nafta", "дизел"]):
        return Advert.FuelType.DIESEL
    if any(k in t for k in ["benzin", "gasoline", "petrol", "benzyna", "бензин"]):
        return Advert.FuelType.GASOLINE
    if any(k in t for k in ["hybrid", "hibrid", "хибрид"]):
        return Advert.FuelType.HYBRID
    if any(k in t for k in ["elekt", "electric", "електри"]):
        return Advert.FuelType.ELECTRIC
    if any(k in t for k in ["gaz", "lpg", "cng", "газ"]):
        # безопасно: если нет GAS в модели — считаем бензином
        return getattr(Advert.FuelType, "GAS", Advert.FuelType.GASOLINE)
    return None


def map_drive(t):
    if not t:
        return None
    t = t.lower()
    if any(k in t for k in ["awd", "4x4", "4wd", "quattro", "allrad"]):
        return Advert.DriveType.AWD
    if any(k in t for k in ["fwd", "front", "vorder", "przedni", "передний"]):
        return Advert.DriveType.FWD
    if any(k in t for k in ["rwd", "heck", "hinter", "tylny", "задний"]):
        return Advert.DriveType.RWD
    return None


# === Основная логика ===
def good_to_payload(good_el, is_first_url=False):
    f = extract_fields_dict(good_el)
    images = extract_images(good_el)
    if not images:
        return None

    name = f.get("Название") or f.get("Title")
    link = f.get("URL")
    price = parse_price(f.get("Цена"))
    currency = f.get("Валюта") or "EUR"

    if not all([name, link, price, currency]):
        return None

    description = f.get("Описание") or f.get("Description") or ""
    address = extract_address_from_description(description)

    return {
        "name": name,
        "link": link,
        "original_link": link,
        "price": price,
        "currency": currency,
        "description": description,
        "address": address,
        "images": images,
        "mileage": parse_int(f.get("Km") or f.get("Przebieg") or f.get("Kilometer")),
        "year": parse_int(f.get("Rok produkcji") or f.get("Rok výroby") or f.get("Год")),
        "power": parse_power_hp(f.get("Leistung") or f.get("Moc")),
        "engine_volume": parse_engine_volume(f.get("Hubraum") or f.get("Pojemność")),
        "transmission": map_transmission(f.get("Getriebe") or f.get("Skrzynia biegów")),
        "fuel": map_fuel(f.get("Kraftstoff") or f.get("Rodzaj paliwa")),
        "drive": map_drive(f.get("Antrieb") or f.get("Napęd")),
        "doors": parse_int(f.get("Türen") or f.get("Liczba drzwi")),
        "color": f.get("Farbe") or f.get("Kolor"),
        "updated_at": now(),
    }


def import_from_url(url, batch_size=500):
    logger.info(f"Скачиваю: {url}")
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Ошибка скачивания {url}: {e}")
        return

    try:
        root = ET.parse(io.BytesIO(resp.content)).getroot()
    except Exception as e:
        logger.error(f"Ошибка XML: {e}")
        return

    goods = root.findall(".//good")
    logger.info(f"Найдено {len(goods)} объявлений")

    to_create = []
    updated = skipped = 0

    for idx, good in enumerate(goods, 1):
        try:
            payload = good_to_payload(good)
            if not payload:
                skipped += 1
                continue

            # Проверяем по link (уникальное поле)
            if Advert.objects.filter(link=payload["link"]).exists():
                Advert.objects.filter(link=payload["link"]).update(**payload)
                updated += 1
            else:
                to_create.append(Advert(**payload))

            if len(to_create) >= batch_size:
                with transaction.atomic():
                    Advert.objects.bulk_create(to_create, ignore_conflicts=True)
                logger.info(f"✅ Сохранено {len(to_create)} новых записей (пакет)")
                to_create.clear()

        except Exception as e:
            logger.error(f"[{idx}] Ошибка: {e}")
            skipped += 1

    # Финальный пакет
    if to_create:
        with transaction.atomic():
            Advert.objects.bulk_create(to_create, ignore_conflicts=True)

    logger.info(f"Готово. Обновлено: {updated}, Пропущено: {skipped}")


# === Запуск ===
if __name__ == "__main__":
    for i, url in enumerate(URLS, 1):
        logger.info(f"--- [{i}/{len(URLS)}] {url}")
        import_from_url(url)