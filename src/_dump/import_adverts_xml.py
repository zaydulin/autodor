import os
import django
import sys
import io
import re
import decimal
import requests
from xml.etree import ElementTree as ET

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_project.settings")
django.setup()

# === Список ссылок на XML ===
URLS = [
    "https://s3.q-parser.ru/export/3435/804/4e86oli/3435804--webauto.de.xml",
    # можешь добавить ещё:
    # "https://example.com/feed2.xml",
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
        if url:
            images.append(url)
            if limit and len(images) >= limit:
                break
    return images
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
    if "schalt" in t or "mechan" in t:
        return Advert.TransmissionType.MANUAL
    if "automatik" in t or "automatic" in t:
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
    if "diesel" in t:
        return Advert.FuelType.DIESEL
    if "benzin" in t or "gasoline" in t or "petrol" in t:
        return Advert.FuelType.GASOLINE
    if "hybrid" in t:
        return Advert.FuelType.HYBRID
    if "elekt" in t or "electric" in t:
        return Advert.FuelType.ELECTRIC
    return None

def map_drive(text):
    if not text:
        return None
    t = text.strip().lower()
    if "allrad" in t or "quattro" in t or "awd" in t or "4x4" in t:
        return Advert.DriveType.AWD
    if "vorder" in t or "front" in t or "fwd" in t:
        return Advert.DriveType.FWD
    if "hinter" in t or "heck" in t or "rwd" in t:
        return Advert.DriveType.RWD
    return None

def good_to_payload(good_el, images_limit=7, is_first_url=False):
    fields = extract_fields_dict(good_el)
    images = extract_images(good_el, images_limit)

    name = fields.get("Название")
    link = fields.get("URL")
    price = parse_price(fields.get("Цена"))
    currency = fields.get("Валюта")

    if not name or not link or price is None or not currency:
        return None

    payload = {
        "name": name,
        "link": link,
        "original_link": link,
        "price": price,
        "currency": currency,
        "description": fields.get("Описание"),
        "images": images or None,
        "subtitle": fields.get("Подзаголовок"),
        "article": fields.get("Артикул"),
        "mileage": parse_int(fields.get("Kilometer")),
        "color": fields.get("Farbe"),
        "doors": parse_int(fields.get("Türen")),
        "power": parse_power_hp(fields.get("Leistung")),
        "engine_volume": parse_engine_volume(fields.get("Hubraum")),
        "year": parse_int(fields.get("Erstzulassung")),
        "transmission": map_transmission(fields.get("Getriebe")),
        "fuel": map_fuel(fields.get("Kraftstoff")),
        "drive": map_drive(fields.get("Antrieb")),
    }

    # Если это первая ссылка — парсим brand и model_auto
    if is_first_url and name:
        parts = name.split(maxsplit=1)
        payload["brand"] = parts[0]
        payload["model_auto"] = parts[1] if len(parts) > 1 else ""

    return payload
def import_from_url(url, update_by="article", is_first_url=False):
    print(f"\nСкачиваю: {url}")
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        return

    try:
        root = ET.parse(io.BytesIO(resp.content)).getroot()
    except Exception as e:
        print(f"Ошибка парсинга XML: {e}")
        return

    goods = root.findall("./good")
    print(f"Найдено {len(goods)} объявлений")

    created = updated = skipped = 0
    for idx, good in enumerate(goods, start=1):
        payload = good_to_payload(good, is_first_url=is_first_url)
        if not payload:
            skipped += 1
            continue

        try:
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
        except Exception as e:
            print(f"[{idx}] Ошибка сохранения: {e}")
            skipped += 1
            continue

        if is_created:
            created += 1
        else:
            updated += 1

    print(f"Готово. Создано: {created}, обновлено: {updated}, пропущено: {skipped}")


# === Запуск для всех ссылок ===
if __name__ == "__main__":
    for i, url in enumerate(URLS):
        import_from_url(url, is_first_url=(i == 0))

