from .core_settings import BASE_DIR
from pathlib import Path
import os.path
from environs import Env

DEBUG = True

STATIC_ROOT = BASE_DIR / '_staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / '_static'
]

env = Env()
env.read_env()

DATABASES = {
    "default": {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        #"ENGINE": "django.db.backends.postgresql",
        #"NAME": env.str("POSTGRES_DB", "db_chester"),
        #"USER": env.str("POSTGRES_USER", "admin"),
        #"PASSWORD": env.str("POSTGRES_PASSWORD", "qwe123QWE"),
        #"HOST": env.str("DJANGO_POSTGRES_HOST", "localhost"),
        #"PORT": env.int("DJANGO_POSTGRES_PORT", 5432),
        'OPTIONS': {
            'timeout': 20,  # Увеличение времени ожидания блокировки
        },
    }
}

CSRF_TRUSTED_ORIGINS = [
    #"https://site.ru",
]

MEDIA_ROOT = os.path.join(BASE_DIR, '_media')



# EMAIL_HOST = 'smtp.beget.com'
# EMAIL_PORT = '465'
# EMAIL_USE_TSL = False
# EMAIL_USE_SSL = True
# EMAIL_HOST_USER = 'info@xn--80akffodct3a4h5a.xn--p1ai'
# #EMAIL_HOST_USER = 'info@памятьземли.рф'
# EMAIL_HOST_PASSWORD = 'OE%&K8s0'
# DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

SMTP_FILE_PATH = Path(MEDIA_ROOT) / 'smtp.py'

try:
    with open(SMTP_FILE_PATH, 'r') as smtp_file:
        exec(smtp_file.read())  # Выполнить содержимое файла
except FileNotFoundError:
    pass