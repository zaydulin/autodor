import os
import requests
from django.conf import settings


def upload_to_yandex_disk(file_path, file_name, folder_path=None):
    """
    Загружает файл на Яндекс.Диск
    """
    try:
        YANDEX_DISK_TOKEN = getattr(settings, 'YANDEX_DISK_TOKEN', None)
        YANDEX_DISK_BASE_PATH = getattr(settings, 'YANDEX_DISK_BASE_PATH', '')

        if not YANDEX_DISK_TOKEN:
            print("Не настроен YANDEX_DISK_TOKEN")
            return False

        # Формируем путь на Яндекс.Диске
        if folder_path:
            remote_path = os.path.join(YANDEX_DISK_BASE_PATH, folder_path, file_name).replace('\\', '/')
        else:
            remote_path = os.path.join(YANDEX_DISK_BASE_PATH, file_name).replace('\\', '/')

        # Получаем URL для загрузки
        url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        headers = {
            'Authorization': f'OAuth {YANDEX_DISK_TOKEN}',
            'Content-Type': 'application/json'
        }
        params = {
            'path': remote_path,
            'overwrite': 'true'
        }

        # Получаем ссылку для загрузки
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        upload_url = response.json()['href']

        # Загружаем файл
        with open(file_path, 'rb') as file:
            upload_response = requests.put(upload_url, data=file)
            upload_response.raise_for_status()

        print(f"Файл загружен на Яндекс.Диск: {remote_path}")
        return True

    except Exception as e:
        print(f"Ошибка загрузки на Яндекс.Диск: {e}")
        return False