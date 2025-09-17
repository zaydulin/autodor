# google_drive_utils.py
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.conf import settings


def upload_to_google_drive(file_path, file_name):
    """
    Загружает файл на Google Drive
    """
    try:
        # Настройки (добавьте в settings.py)
        SERVICE_ACCOUNT_FILE = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_FILE', None)
        FOLDER_ID = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None)

        if not SERVICE_ACCOUNT_FILE or not FOLDER_ID:
            print("Не настроены Google Drive credentials")
            return False

        # Аутентификация
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        service = build('drive', 'v3', credentials=credentials)

        # Метаданные файла
        file_metadata = {
            'name': file_name,
            'parents': [FOLDER_ID]
        }

        # Загрузка файла
        media = MediaFileUpload(file_path, resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"Файл загружен на Google Drive. ID: {file.get('id')}")
        return True

    except Exception as e:
        print(f"Ошибка загрузки на Google Drive: {e}")
        return False