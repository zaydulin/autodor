from django.contrib import admin
from django.utils.html import format_html
from .models import *

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['phone', 'display_avatar', 'get_gender_display']
    list_display_links = ['phone', 'display_avatar', 'get_gender_display']

    def display_avatar(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" alt="{}" height="100" />', obj.avatar.url, obj.username)
        return ''

    display_avatar.short_description = 'Аватарка'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['get_status_display', 'user']

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'type', 'create']

@admin.register(Cards)
class CardsAdmin(admin.ModelAdmin):
    list_display = ['card', 'status', 'user']