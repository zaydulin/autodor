import os
import firebase_admin
from firebase_admin import credentials

# Относительный путь к JSON-файлу
current_dir = os.path.dirname(os.path.abspath(__file__))
firebase_credentials_path = os.path.join(current_dir, "bahtrucks-firebase-adminsdk-fbsvc-5ac8009ced.json")

# Инициализация Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials_path)
    firebase_admin.initialize_app(cred)
