import os
from django.core.files.base import ContentFile
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import AdvertDocument,AdvertAplication
from webmain.models import SettingsGlobale


def default_settings_file():
    settings = SettingsGlobale.objects.first()
    if not settings:
        return None
    for idx in range(1, 9):
        f = getattr(settings, f"document_file{idx}", None)
        if f and getattr(f, "name", ""):
            return f
    return None

@receiver(pre_save, sender=AdvertDocument)
def fill_document_file_from_settings(sender, instance, **kwargs):
    if instance.file and instance.file.name:
        return #
    default_file = default_settings_file()
    if not default_file:
        return

    try:
        with default_file.open("rb") as fp:
            content = fp.read()
            instance.file.save(os.path.basename(default_file.name), ContentFile(content), save=False)
    except Exception:
        pass



