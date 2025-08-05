from django import template
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Q, Max, Subquery, OuterRef
from useraccount.models import Notification


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
