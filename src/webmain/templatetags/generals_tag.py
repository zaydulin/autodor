from django import template
from django.db.models import Count
from django.middleware.csrf import get_token

from webmain.forms import SubscriptionForm
from webmain.models import SettingsGlobale, ContactPage, Pages, CategorysBlogs

register = template.Library()


@register.simple_tag
def get_settings_first():
    return SettingsGlobale.objects.first()


@register.simple_tag
def get_contacts_first():
    return ContactPage.objects.first()

@register.simple_tag
def get_pages():
    return Pages.objects.all().filter(publishet=True)

@register.simple_tag
def get_categories_without_parent(current_domain):
    return CategorysBlogs.objects.filter(parent__isnull=True).order_by('name')

@register.simple_tag
def get_categories_without_parent_with_products(current_domain):
    categories = CategorysBlogs.objects.filter(parent__isnull=True).annotate(
        product_count=Count('products')
    ).order_by('name')
    return categories

@register.simple_tag(takes_context=True)
def render_subscription_form(context):
    request = context['request']
    form = SubscriptionForm()
    csrf_token = get_token(request)

    return {
        'form': form,
        'csrf_token': csrf_token
    }