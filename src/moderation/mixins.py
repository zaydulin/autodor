# moderation/mixins.py
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.apps import apps
import json


class TrackChangesMixin(models.Model):
    """
    Миксин для автоматического отслеживания изменений в полях модели.
    Сохраняет старое состояние перед сохранением.
    """

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_state = self._capture_state()

    def _capture_state(self):
        """Захватить текущее состояние модели"""
        state = {}
        for field in self._meta.fields:
            if field.name not in ['id', 'created_at', 'updated_at']:
                try:
                    value = getattr(self, field.name)
                    # Конвертируем модели, даты и другие сложные типы
                    if isinstance(value, models.Model):
                        value = f"{value.__class__.__name__}:{value.pk}"
                    elif hasattr(value, 'isoformat'):  # datetime/date
                        value = value.isoformat()
                    state[field.name] = value
                except (AttributeError, ValueError):
                    state[field.name] = None
        return state

    def get_changed_fields(self, new_state):
        """Получить список измененных полей"""
        changed = {}

        for field_name, old_value in self._original_state.items():
            new_value = new_state.get(field_name)

            # Сравниваем значения
            if old_value != new_value:
                changed[field_name] = {
                    'old': old_value,
                    'new': new_value,
                    'field_verbose': self._get_field_verbose_name(field_name)
                }

        # Проверяем новые поля, которых не было в оригинальном состоянии
        for field_name, new_value in new_state.items():
            if field_name not in self._original_state:
                changed[field_name] = {
                    'old': None,
                    'new': new_value,
                    'field_verbose': self._get_field_verbose_name(field_name)
                }

        return changed

    def _get_field_verbose_name(self, field_name):
        """Получить человекочитаемое имя поля"""
        try:
            field = self._meta.get_field(field_name)
            return field.verbose_name if hasattr(field, 'verbose_name') else field_name
        except:
            return field_name

    def update_original_state(self):
        """Обновить оригинальное состояние после сохранения"""
        self._original_state = self._capture_state()


# Сигналы для отслеживания изменений
@receiver(pre_save)
def capture_pre_save_state(sender, instance, **kwargs):
    """Захватить состояние перед сохранением"""
    if hasattr(instance, '_original_state'):
        # Обновляем состояние перед сохранением
        instance._original_state = instance._capture_state()