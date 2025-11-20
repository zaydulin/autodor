import json
import os
from urllib.parse import urlparse
from django.db.models.signals import m2m_changed

import requests
from django.core.files.base import ContentFile
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import AdvertDocument, AdvertAplication, AdvertApplicationImage, Advert
from webmain.models import SettingsGlobale
import logging

# Логирование
logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=AdvertAplication.user_menager.through)
def update_user_from_menager(sender, instance, action, pk_set, **kwargs):
    """
    Обновляет поле user при изменении user_menager
    Добавляет менеджеров в user, но не удаляет других пользователей
    """
    if action == "post_add":
        # Добавляем новых менеджеров в поле user
        new_managers = instance.user_menager.all()
        current_users = set(instance.user.all())

        # Добавляем только тех, кого еще нет в user
        for manager in new_managers:
            if manager not in current_users:
                instance.user.add(manager)

    elif action == "post_remove":
        # Удаляем менеджеров из user только если их нет в user_drivers
        removed_manager_ids = pk_set
        current_drivers = set(instance.user_drivers.values_list('id', flat=True))

        # Удаляем только тех менеджеров, которые не являются водителями
        for manager_id in removed_manager_ids:
            if manager_id not in current_drivers:
                instance.user.remove(manager_id)


@receiver(m2m_changed, sender=AdvertAplication.user_drivers.through)
def update_user_from_drivers(sender, instance, action, pk_set, **kwargs):
    """
    Обновляет поле user при изменении user_drivers
    Добавляет водителей в user, но не удаляет других пользователей
    """
    if action == "post_add":
        # Добавляем новых водителей в поле user
        new_drivers = instance.user_drivers.all()
        current_users = set(instance.user.all())

        # Добавляем только тех, кого еще нет в user
        for driver in new_drivers:
            if driver not in current_users:
                instance.user.add(driver)

    elif action == "post_remove":
        # Удаляем водителей из user только если их нет в user_menager
        removed_driver_ids = pk_set
        current_managers = set(instance.user_menager.values_list('id', flat=True))

        # Удаляем только тех водителей, которые не являются менеджерами
        for driver_id in removed_driver_ids:
            if driver_id not in current_managers:
                instance.user.remove(driver_id)

# В сигнале
@receiver(pre_save, sender=Advert)
def check_images_before_save(sender, instance, **kwargs):
    """
    Сигнал для проверки ссылок на изображения.
    Если нет валидных изображений, не сохраняем поле вообще.
    """
    if hasattr(instance, 'images') and instance.images:
        valid_images = []
        for image_url in instance.images:
            try:
                response = requests.head(image_url, allow_redirects=True, timeout=5)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if content_type and content_type.startswith('image/'):
                        valid_images.append(image_url)
            except requests.RequestException:
                continue

        if valid_images:
            instance.images = valid_images
        else:
            # Удаляем атрибут (поле не будет сохранено в БД)
            instance.images = None


def default_settings_file():
    settings = SettingsGlobale.objects.first()
    if not settings:
        return None
    for idx in range(1, 9):
        f = getattr(settings, f"document_file{idx}", None)
        if f and getattr(f, "name", ""):
            return f
    return None

@receiver(pre_save, sender=AdvertDocument)
def fill_document_file_from_settings(sender, instance, **kwargs):
    if instance.file and instance.file.name:
        return #
    default_file = default_settings_file()
    if not default_file:
        return

    try:
        with default_file.open("rb") as fp:
            content = fp.read()
            instance.file.save(os.path.basename(default_file.name), ContentFile(content), save=False)
    except Exception:
        pass

@receiver(post_save, sender=AdvertAplication)
def download_advert_images(sender, instance, created, **kwargs):
    if not created:
        return  # Обрабатываем только создание заявки

    advert = instance.advert
    images_urls = advert.images or []

    for url in images_urls:
        try:
            response = requests.get(url)
            response.raise_for_status()

            # Получить имя файла из URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = 'image.jpg'

            # Создать объект ContentFile
            image_content = ContentFile(response.content)

            # Создать и сохранить изображение
            advert_image = AdvertApplicationImage(application=instance)
            advert_image.image.save(filename, image_content, save=True)

        except Exception as e:
            # Логировать ошибку или пропустить
            print(f"Ошибка при скачивании {url}: {e}")




