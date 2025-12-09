from django import template
from django.contrib.auth import get_user_model
from django.utils.timesince import timesince
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Q, Max, Subquery, OuterRef
from useraccount.models import Notification
import json


register = template.Library()

@register.simple_tag
def get_notifications_count(user):
    if user.is_authenticated:
        notification = Notification.objects.filter(user=user, status=1).first()
        if notification:
            return Notification.objects.filter(user=user, status=1).count()
    return 0

@register.simple_tag
def get_unread_notifications(user):
    if user.is_authenticated:
        return Notification.objects.filter(user=user, status=1).order_by('-created_at')[:4]
    return []

@register.filter
def dict_get(d, key):
    if not d:
        return None
    return d.get(key)

@register.filter
def split(value, key):
    """
    Делит строку по key и возвращает список
    """
    return value.split(key)

@register.simple_tag(takes_context=True)
def unread_notifications(context, limit=5):
    """
    Возвращает последние `limit` непрочитанных уведомлений для текущего пользователя.
    """
    user = context.get("request").user
    if not user or user.is_anonymous:
        return []

    qs = Notification.objects.filter(user=user, status=1).order_by("-created_at")[:limit]
    notifications = []

    for n in qs:
        try:
            payload = json.loads(n.message)
        except Exception:
            payload = {"text": n.message}

        notifications.append({
            "raw": n,
            "payload": payload,
            "created_at": n.created_at,
        })

    return notifications

@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    """
    Возвращает количество непрочитанных уведомлений для текущего пользователя.
    """
    user = context.get("request").user
    if not user or user.is_anonymous:
        return 0

    return Notification.objects.filter(user=user, status=1).count()


@register.filter
def time_since_updated(value):
    """
    Возвращает строку вида 'Обновлено X назад'
    """
    if not value:
        return "Обновлено недавно"
    now = timezone.now()
    delta = now - value
    # Используем встроенную функцию timesince
    timesince_str = timesince(value, now)
    # Можно добавить обработку для "только минут" или "часов"
    # Например, если прошло менее часа
    total_seconds = delta.total_seconds()
    if total_seconds < 60:
        return "Обновлено только что"
    elif total_seconds < 3600:
        minutes = int(total_seconds // 60)
        return f"Обновлено {minutes} минут назад"
    elif total_seconds < 86400:
        hours = int(total_seconds // 3600)
        return f"Обновлено {hours} часов назад"
    else:
        days = int(total_seconds // 86400)
        return f"Обновлено {days} дней назад"