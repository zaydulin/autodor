from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SettingsGlobale, ContactPage, AboutPage, HomePage, Seo

@receiver(post_save, sender=SettingsGlobale)
def create_related_pages(sender, instance, created, **kwargs):
    if created:
        # Создание страницы "ContactPage"
        ContactPage.objects.create(setting=instance)

        # Создание страницы "AboutPage"
        AboutPage.objects.create(setting=instance)

        # Создание страницы "HomePage"
        HomePage.objects.create(setting=instance)

        # Создание SEO записей для всех `pagetype`
        for page_type, page_name in Seo.PAGE_CHOICE:
            Seo.objects.create(
                pagetype=page_type,
                title=page_name,  # Используем значение из PAGE_CHOICE
                setting=instance
            )
