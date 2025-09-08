from django.apps import AppConfig


class MobiledevaiseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mobiledevaise'
    def ready(self):
        pass
