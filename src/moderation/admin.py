from django.contrib import admin
from .models import *

import nested_admin
from django.utils.html import format_html

@admin.register(Advert)
class AdvertAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "price", "currency", "year",
        "transmission", "fuel", "drive", "created_at", "preview_image"
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "article", "description")
    list_filter = ("currency", "year", "transmission", "fuel", "drive", "color")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def preview_image(self, obj):
        """Показать первое изображение из списка"""
        if obj.images and isinstance(obj.images, list) and len(obj.images) > 0:
            return format_html('<img src="{}" width="60" style="object-fit:cover;border-radius:4px;" />', obj.images[0])
        return "-"
    preview_image.short_description = "Фото"




@admin.register(AdvertAplication)
class AdvertAplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "advert", "users_list", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("advert__name", "user__username", "user__email")
    date_hierarchy = "created_at"
    filter_horizontal = ("user",)  # удобный выбор нескольких пользователей
    autocomplete_fields = ("advert",)  # если включишь autocomplete для объявлений

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("advert").prefetch_related("user")

    def users_list(self, obj):
        # красиво выводим M2M пользователей
        names = [getattr(u, "get_full_name", lambda: "")() or u.username for u in obj.user.all()]
        return ", ".join(names) or "—"
    users_list.short_description = "Пользователи"



admin.site.register(AdvertExpense)
admin.site.register(CallSession)
admin.site.register(ChatMessage)










# Register your models here.

# class TicketCommentMediaInline(nested_admin.NestedTabularInline):
#     model = TicketCommentMedia
#     extra = 1
#
#
# class TicketCommentInline(nested_admin.NestedTabularInline):
#     model = TicketComment
#     extra = 1
#     inlines = [TicketCommentMediaInline]
#
#     # Удаляем поле `author` из формы редактирования
#     def get_formset(self, request, obj=None, **kwargs):
#         formset = super().get_formset(request, obj, **kwargs)
#         formset.form.base_fields.pop('author', None)  # Скрываем поле `author` в inline
#         formset.form.base_fields.pop('ftp_access_message', None)  # Hide the 'ftp_access_message' field
#         return formset
#
#     def get_readonly_fields(self, request, obj=None):
#         if obj:  # Если объект существует, делаем его только для чтения
#             return ['author', 'ticket']
#         return []
#
#     def has_change_permission(self, request, obj=None):
#         if obj:
#             return False  # Запрет на изменение существующих объектов
#         return True  # Разрешить изменение новых объектов
#
#     def has_delete_permission(self, request, obj=None):
#         if obj:
#             return False  # Запрет на удаление существующих объектов
#         return True  # Разрешить удаление новых объектов
#
#
# # Admin для `Ticket`
# @admin.register(Ticket)
# class TicketAdmin(nested_admin.NestedModelAdmin):
#     list_display = ['date', 'status']
#     list_filter = ['status', 'date']
#     inlines = [TicketCommentInline]
#
#     # Только для чтения поля для `Ticket`, без поля `author`
#     readonly_fields = ()  # Убедитесь, что нет полей, которые вызовут ошибки
#     # Метод для исключения полей из формы
#     def get_form(self, request, obj=None, **kwargs):
#         form = super().get_form(request, obj, **kwargs)
#         return form
#
#     def get_readonly_fields(self, request, obj=None):
#         if obj:  # When editing an existing object
#             return self.readonly_fields + ('author',)
#         return self.readonly_fields
#
