import os
from celery import Celery

# Устанавливаем переменную окружения для настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_project.settings')

app = Celery('_project')

# Используем строку конфигурации Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическая загрузка задач из приложений
app.autodiscover_tasks()

# Настройки по умолчанию
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# Конфигурация для периодических задач (если потребуется)
# app.conf.beat_schedule = {
#     'task_name': {
#         'task': 'app.tasks.task_name',
#         'schedule': crontab(minute=0, hour=0),
#     },
# }
