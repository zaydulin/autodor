from django.contrib import admin
from .models import *

import nested_admin

# Register your models here.

class TicketCommentMediaInline(nested_admin.NestedTabularInline):
    model = TicketCommentMedia
    extra = 1


class TicketCommentInline(nested_admin.NestedTabularInline):
    model = TicketComment
    extra = 1
    inlines = [TicketCommentMediaInline]

    # Удаляем поле `author` из формы редактирования
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields.pop('author', None)  # Скрываем поле `author` в inline
        formset.form.base_fields.pop('ftp_access_message', None)  # Hide the 'ftp_access_message' field
        return formset

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Если объект существует, делаем его только для чтения
            return ['author', 'ticket']
        return []

    def has_change_permission(self, request, obj=None):
        if obj:
            return False  # Запрет на изменение существующих объектов
        return True  # Разрешить изменение новых объектов

    def has_delete_permission(self, request, obj=None):
        if obj:
            return False  # Запрет на удаление существующих объектов
        return True  # Разрешить удаление новых объектов


# Admin для `Ticket`
@admin.register(Ticket)
class TicketAdmin(nested_admin.NestedModelAdmin):
    list_display = ['date', 'status']
    list_filter = ['status', 'date']
    inlines = [TicketCommentInline]

    # Только для чтения поля для `Ticket`, без поля `author`
    readonly_fields = ()  # Убедитесь, что нет полей, которые вызовут ошибки
    # Метод для исключения полей из формы
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form

    def get_readonly_fields(self, request, obj=None):
        if obj:  # When editing an existing object
            return self.readonly_fields + ('author',)
        return self.readonly_fields

