import os
import requests
from django.conf import settings


def check_token_validity():
    """Проверяет валидность токена Яндекс.Диска"""
    YANDEX_DISK_TOKEN = getattr(settings, 'YANDEX_DISK_TOKEN', None)

    if not YANDEX_DISK_TOKEN:
        print("Токен не настроен")
        return False

    url = 'https://cloud-api.yandex.net/v1/disk/'
    headers = {'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("Токен валиден")
            return True
        else:
            print(f"Токен невалиден: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка проверки токена: {e}")
        return False


def upload_to_yandex_disk(file_path, file_name, folder_path=None):
    """
    Загружает файл на Яндекс.Диск с улучшенной обработкой ошибок
    """
    token = "y0__xDW_u-2CBj4tjogr8PyvRTJ_Pe5GDabgbnD2zC0ldkWvSubPw"
    base_path = "audio_backups"

    try:
        # Формируем конечный путь
        if folder_path:
            remote_path = f"{base_path}/{folder_path}/{file_name}"
        else:
            remote_path = f"{base_path}/{file_name}"

        remote_path = remote_path.replace('//', '/')
        print(f"📁 Путь: {remote_path}")

        # 1. Создаем папку audio_backups если нужно
        if folder_path:
            full_folder_path = f"{base_path}/{folder_path}"
        else:
            full_folder_path = base_path

        # Создаем папку рекурсивно
        create_folder(token, full_folder_path)

        # 2. Получаем ссылку для загрузки
        url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        headers = {'Authorization': f'OAuth {token}'}
        params = {'path': remote_path, 'overwrite': 'true'}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
            return False

        upload_url = response.json()['href']
        print("✅ Получена ссылка для загрузки")

        # 3. Загружаем файл
        with open(file_path, 'rb') as f:
            upload_response = requests.put(upload_url, data=f)

        print(f"📤 Статус загрузки: {upload_response.status_code}")

        if upload_response.status_code in [200, 201, 202]:
            print("✅ Файл успешно загружен!")
            return True
        else:
            print(f"❌ Ошибка загрузки: {upload_response.text}")
            return False

    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return False


def create_folder(token, folder_path):
    """Рекурсивно создает папку"""
    url = 'https://cloud-api.yandex.net/v1/disk/resources'
    headers = {'Authorization': f'OAuth {token}'}
    params = {'path': folder_path}

    response = requests.put(url, headers=headers, params=params)

    if response.status_code in [200, 201]:
        print(f"✅ Создана папка: {folder_path}")
    elif response.status_code == 409:
        print(f"✅ Папка существует: {folder_path}")
    else:
        print(f"⚠️ Не удалось создать папку: {response.status_code}")