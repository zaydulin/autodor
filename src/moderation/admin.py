from django.contrib import admin
from .models import *

import nested_admin
from django.utils.html import format_html


@admin.register(Advert)
class AdvertAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "car_brand", "car_model",
        "price", "currency",
        "mileage", "color", "doors", "power", "engine_volume", "year",
        "updated_at", "created_at", "transmission", "fuel", "drive", "preview_image"
    )
    list_display_links = ("id", "name")

    # Поиск по этим полям (уже работает!)
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
from django.contrib.auth import get_user_model



@admin.register(AdvertAplication)
class AdvertAplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "users_list",
        "order_number",
        "status",
        "advert_title",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "user__email", "advert_name", "advert_id")
    date_hierarchy = "created_at"
    filter_horizontal = ("user", "user_menager", "user_drivers")

    def get_queryset(self, request):
        # ВСЕГДА работаем с default для заявок
        qs = super().get_queryset(request)
        return qs.using("default")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Главное место, где падает ошибка:
        по умолчанию админка берёт queryset из неправильной БД.
        Здесь мы жёстко говорим: пользователей брать из default.
        """
        if db_field.name in ("user", "user_menager", "user_drivers"):
            User = get_user_model()  # useraccount.Profile
            kwargs["queryset"] = User.objects.using("default").all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def users_list(self, obj):
        """Красивый вывод M2M пользователей"""
        users = obj.user.all()
        names = [
            (u.get_full_name() if hasattr(u, "get_full_name") else "") or u.username
            for u in users
        ]
        return ", ".join(names) or "—"

    users_list.short_description = "Пользователи"

    def advert_title(self, obj):
        """
        Показать название объявления:
        - сначала пытаемся подтянуть актуальное из внешней БД (get_advert),
        - если не нашли – используем сохранённое advert_name.
        """
        advert_obj = obj.get_advert()
        if advert_obj:
            return advert_obj.name
        return obj.advert_name or "—"

    advert_title.short_description = "Объявление"


admin.site.register(AdvertExpense)
admin.site.register(CallSession)
admin.site.register(ChatMessage)
admin.site.register(AdvertDocument)
admin.site.register(Path)
admin.site.register(PathResponsibility)
admin.site.register(CarBrand)
admin.site.register(AdvertAplicationGallery)
admin.site.register(AdvertApplicationLog)

@admin.register(ExpenseMask)
class ExpenseMaskAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ("name","pagetype",)
    search_fields = ("name",)

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'type', 'create']










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
