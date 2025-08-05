from django.apps import AppConfig


class WebmainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webmain'

    def ready(self):
        import webmain.signals

