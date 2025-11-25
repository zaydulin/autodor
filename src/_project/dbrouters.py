# _project/dbrouters.py
from django.apps import apps

class AdvertRouter:
    adverts_models = {  # модели, которые живут в БД "adverts"
        ("moderation", "advert"),
        ("moderation", "carbrand"),
        ("moderation", "carmodel"),
    }

    def _is_adverts_model(self, model):
        return (model._meta.app_label, model._meta.model_name) in self.adverts_models

    # ---- ЧТЕНИЕ ----
    def db_for_read(self, model, **hints):
        if self._is_adverts_model(model):
            return "adverts"
        return None  # default

    # ---- ЗАПИСЬ ----
    def db_for_write(self, model, **hints):
        if self._is_adverts_model(model):
            return "adverts"
        return None

    # ---- СВЯЗИ ----
    def allow_relation(self, obj1, obj2, **hints):
        # разрешаем любые связи (иначе ValueError)
        return True

    # ---- МИГРАЦИИ ----
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Мигрируем Advert, CarBrand, CarModel только в базу "adverts"
        if (app_label, model_name) in self.adverts_models:
            return db == "adverts"

        # В adverts не мигрируем НИЧЕГО кроме этих 3 моделей
        if db == "adverts":
            return False

        # Всё остальное — в default
        return None




