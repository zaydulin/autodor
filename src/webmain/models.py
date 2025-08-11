from django.db import models
from ckeditor.fields import RichTextField
from django.urls import reverse
from django.conf import settings
from django.core.validators import (FileExtensionValidator)
import os


class Seo(models.Model):
    """Персона"""
    PAGE_CHOICE = [
        (1, 'Новости'),
        (2, 'Поиск'),
        (3, 'Контакты'),
        (4, 'ЧаВО'),
        (5, 'Авторизация'),
        (6, 'Регистрация'),
        (7, 'Сбросить пароль'),
        (8, 'Профиль'),
        (9, 'Сменить пароль'),
        (10, 'Паспортные данные'),
        (11, 'Уведомление'),

    ]
    pagetype = models.PositiveSmallIntegerField('Странца', unique=True, choices=PAGE_CHOICE, blank=False, default=1)
    previev = models.FileField(upload_to='settings/%Y/%m/%d/', blank=True, null=True, verbose_name="Превью", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(verbose_name="Мета-заголовок", max_length=150, blank=True, null=True,)
    metadescription = models.CharField(verbose_name="Мета-описание", max_length=255, blank=True, null=True,)
    propertytitle = models.CharField(verbose_name="Мета-заголовок ссылки", max_length=150, blank=True, null=True,)
    propertydescription = models.CharField(verbose_name="Мета-описание ссылки", max_length=255, blank=True, null=True,)
    setting = models.ForeignKey("SettingsGlobale", verbose_name='Настройки', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = "Сео страницы"
        verbose_name_plural = "Сео страниц"


class SettingsGlobale(models.Model):
    """Настройки сайта"""
    logo = models.FileField("Логотип",  upload_to='settings/%Y/%m/%d/', blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    doplogo = models.FileField("Дополнительный логотип",  upload_to='settings/%Y/%m/%d/', blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    logo_white = models.FileField("Логотип белый",  upload_to='settings/%Y/%m/%d/', blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    doplogo_white = models.FileField("Дополнительный логотип белый",  upload_to='settings/%Y/%m/%d/', blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    favicon = models.FileField("Фавикон", upload_to='settings/%Y/%m/%d/', blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    paymentmetod = models.FileField("Методы оплаты", upload_to='settings/%Y/%m/%d/', blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    name = models.CharField("Название", max_length=500, blank=True, null=True)
    content = models.CharField("Копирайт", max_length=500, blank=True, null=True)
    description = RichTextField("Описание", blank=True, null=True)
    phone = models.CharField("Телефон", max_length=500, blank=True, null=True)
    map = models.CharField("Карта", max_length=500, blank=True, null=True)
    phones = models.TextField("Телефоны", blank=True, null=True)
    address = models.TextField("Адреса", blank=True, null=True)
    office_hourse = models.TextField("График", blank=True, null=True)
    message_header = models.TextField("Шапка сообщения письма", blank=True, null=True)
    message_footer = models.TextField("Подвал сообщения письма", blank=True, null=True)
    yandex_metrica = models.TextField("Яндекс метрика", blank=True, null=True)
    google_analitic = models.TextField("Гугл аналитика", blank=True, null=True)
    email_host = models.TextField("Email Site HOST", blank=True, null=True)
    default_from_email = models.TextField("Email Site HOST", blank=True, null=True)
    email_port = models.TextField("Email Site PORT", blank=True, null=True)
    email_host_user = models.TextField("Email Site User", blank=True, null=True)
    email_host_password = models.TextField("Email Site Password", blank=True, null=True)
    email_use_tls = models.BooleanField("Use TLS", default=False, blank=True, null=True)
    email_use_ssl = models.BooleanField("Use SSL", default=False, blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Сначала сохраняем модель
        super().save(*args, **kwargs)

        # Путь к файлу, куда будем сохранять данные
        file_path = os.path.join(settings.BASE_DIR, '_media\smtp.py')

        # Сохраняем данные в текстовый файл
        with open(file_path, 'w') as f:
            f.write(f"EMAIL_HOST = '{self.email_host}'\n")
            f.write(f"EMAIL_PORT = '{self.email_port}'\n")
            f.write(f"EMAIL_USE_TLS = {self.email_use_tls}\n")
            f.write(f"EMAIL_USE_SSL = {self.email_use_ssl}\n")
            f.write(f"EMAIL_HOST_USER = '{self.email_host_user}'\n")
            f.write(f"EMAIL_HOST_PASSWORD = '{self.email_host_password}'\n")
            f.write(f"DEFAULT_FROM_EMAIL = '{self.default_from_email}'\n")

    class Meta:
        verbose_name = "Настройка сайта"
        verbose_name_plural = "Настройки сайта"


class ContactPage(models.Model):
    """Настройки контакты"""
    image = models.FileField(upload_to='contact/%Y/%m/%d/', blank=True, null=True, verbose_name="Изображение", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(verbose_name="Заголовок", max_length=350)
    description = models.CharField(verbose_name="Описание", max_length=550)
    setting = models.ForeignKey("SettingsGlobale", verbose_name='Настройки', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = "Страница контакты"
        verbose_name_plural = "Страницы контакты"

class ContactPageInformation(models.Model):
    """Настройки контакты"""
    CONTACT_CHOICE = {
        (
            "Номера телефонов",
            (
                ('phone_default', 'Номер телефона по умолчанию',),
                ('phone', 'Остальные номера телефонов'),
            ),
        ),
        (
            "Электроная почта",
            (
                ('email_default', 'Почта по умолчанию',),
                ('email', 'Остальные почты'),
            ),
        ),
        (
            "Адресса",
            (
                ('address_default', 'Адресс по умолчанию',),
                ('address', 'Остальные адресса'),
            ),
        ),
        (
            "Карты",
            (
                ('map_default', 'Карта по умолчанию',),
                ('map', 'Остальные карты'),
            ),
        ),

    }
    page_type = models.CharField("Тип", max_length=50, choices=CONTACT_CHOICE)
    image = models.FileField(upload_to='contact/%Y/%m/%d/', blank=True, null=True, verbose_name="Изображение", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title_contact = models.CharField(verbose_name="Заголовок контактов", max_length=350)
    description_contact = models.CharField(verbose_name="Описание контактов", max_length=550)
    information_contact = models.CharField(verbose_name="Информация контактов", max_length=350)
    contact_pages = models.ForeignKey("ContactPage", verbose_name='Настройки', related_name="contact_page", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = "Страница контакты (информация)"
        verbose_name_plural = "Страницы контакты (информация)"


class AboutPage(models.Model):
    """Страница о нас (о компании)"""
    previev = models.FileField(upload_to='settings/%Y/%m/%d/', blank=True, null=True, verbose_name="Превью", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(verbose_name="Мета-заголовок", max_length=150, blank=True, null=True,)
    metadescription = models.CharField(verbose_name="Мета-описание", max_length=255, blank=True, null=True,)
    propertytitle = models.CharField(verbose_name="Мета-заголовок ссылки", max_length=150, blank=True, null=True,)
    propertydescription = models.CharField(verbose_name="Мета-описание ссылки", max_length=255, blank=True, null=True,)
    setting = models.ForeignKey("SettingsGlobale", verbose_name='Настройки', on_delete=models.CASCADE, blank=True, null=True)
    text = models.CharField(verbose_name="текст", max_length=255, blank=True, null=True,)
    description = models.TextField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Страница О нас"
        verbose_name_plural = "Страницы О нас"

    def save(self, *args, **kwargs):
        if not self.pk and AboutPage.objects.exists():
            raise ValidationError("Можно создать только одну страницу 'О нас'")
        return super().save(*args, **kwargs)



class HomePage(models.Model):
    """Настройки сайта"""
    previev = models.FileField(upload_to='settings/%Y/%m/%d/', blank=True, null=True, verbose_name="Превью", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(verbose_name="Мета-заголовок", max_length=150, blank=True, null=True,)
    metadescription = models.CharField(verbose_name="Мета-описание", max_length=255, blank=True, null=True,)
    propertytitle = models.CharField(verbose_name="Мета-заголовок ссылки", max_length=150, blank=True, null=True,)
    propertydescription = models.CharField(verbose_name="Мета-описание ссылки", max_length=255, blank=True, null=True,)
    setting = models.ForeignKey("SettingsGlobale", verbose_name='Настройки', on_delete=models.CASCADE, blank=True, null=True)
    text = models.CharField(verbose_name="текст", max_length=255, blank=True, null=True,)
    description = models.TextField("Описание", blank=True, null=True)

    class Meta:
        verbose_name = "Главная страница"
        verbose_name_plural = "Главные страницы"


class Pages(models.Model):
    """Страницы"""
    PAGETYPE = [
        (1, 'Стандартная'),
        (2, 'Пользовательское соглашение'),
        (3, 'Политика конфедециальности'),
        (4, 'Политика Cookie - Файлов'),
        (5, 'Согласия на обработку персональных данных'),
    ]
    pagetype = models.PositiveSmallIntegerField('Тип', choices=PAGETYPE, blank=False, default=1)
    name = models.CharField("Название", max_length=250)
    description = RichTextField("Описание", blank=True, null=True)
    slug = models.SlugField(max_length=140, unique=True)
    previev = models.FileField(upload_to='pages/%Y/%m/%d/', blank=True, null=True, verbose_name="Превью", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(verbose_name="Мета-заголовок", max_length=150, blank=True, null=True,)
    metadescription = models.CharField(verbose_name="Мета-описание", max_length=255, blank=True, null=True,)
    propertytitle = models.CharField(verbose_name="Мета-заголовок ссылки", max_length=150, blank=True, null=True,)
    propertydescription = models.CharField(verbose_name="Мета-описание ссылки", max_length=255, blank=True, null=True,)
    publishet = models.BooleanField("Опубликован", default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Страница"
        verbose_name_plural = "Страницы"


class Faqs(models.Model):
    """Часто задаваемые вопросы """
    question = models.TextField(blank=True, null=True, verbose_name='Вопрос')
    answer = models.TextField(blank=True, null=True, verbose_name='Ответ', default=' ')
    create = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    update = models.DateTimeField(auto_now=True, blank=True, null=True)
    publishet = models.BooleanField("Опубликован", default=False)


    class Meta:
        verbose_name = "Часто задаваемые вопросы"
        verbose_name_plural = "Часто задаваемые вопрос"


class CategorysBlogs(models.Model):
    """Категории"""
    name = models.CharField(max_length=150, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, blank=True, null=True, verbose_name='URL')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Родитель')
    cover = models.FileField("Обложка категории",   upload_to="category/%Y/%m/%d/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    icon = models.FileField("Иконка категории",   upload_to="category/%Y/%m/%d/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    image = models.FileField("Картинка категории",   upload_to="category/%Y/%m/%d/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    previev = models.FileField(upload_to='category/%Y/%m/%d/', blank=True, null=True, verbose_name="Превью", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(verbose_name="Мета-заголовок", max_length=150, blank=True, null=True,)
    metadescription = models.CharField(verbose_name="Мета-описание", max_length=255, blank=True, null=True,)
    propertytitle = models.CharField(verbose_name="Мета-заголовок ссылки", max_length=150, blank=True, null=True,)
    propertydescription = models.CharField(verbose_name="Мета-описание ссылки", max_length=255, blank=True, null=True,)
    publishet = models.BooleanField("Опубликован", default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория новости"
        verbose_name_plural = "Категории новости"


class TagsBlogs(models.Model):
    """Метки"""
    name = models.CharField(max_length=150, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, blank=True, null=True, verbose_name='URL')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    cover = models.FileField("Обложка метки",   upload_to="tags/%Y/%m/%d/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    icon = models.FileField("Иконка метки",   upload_to="tags/%Y/%m/%d/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    image = models.FileField("Картинка метки",   upload_to="tags/%Y/%m/%d/", blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    previev = models.FileField(upload_to='tags/%Y/%m/%d/', blank=True, null=True, verbose_name="Превью", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(verbose_name="Мета-заголовок", max_length=150, blank=True, null=True,)
    metadescription = models.CharField(verbose_name="Мета-описание", max_length=255, blank=True, null=True,)
    propertytitle = models.CharField(verbose_name="Мета-заголовок ссылки", max_length=150, blank=True, null=True,)
    propertydescription = models.CharField(verbose_name="Мета-описание ссылки", max_length=255, blank=True, null=True,)
    publishet = models.BooleanField("Опубликован", default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Метка новости"
        verbose_name_plural = "Метки новости"


class Blogs(models.Model):
    """Блог"""
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Авторы', on_delete=models.CASCADE, blank=True, null=True)
    resource = models.CharField("Источник", max_length=550, blank=True, null=True)
    category = models.ManyToManyField(CategorysBlogs, verbose_name="Категории", blank=True)
    tags = models.ManyToManyField(TagsBlogs, verbose_name="Метки", blank=True)
    name = models.CharField("Название", max_length=250)
    description = RichTextField("Описание", blank=True, null=True)
    previev = models.FileField(upload_to='blogs/%Y/%m/%d/', blank=True, null=True, verbose_name="Превью", default='default/imagegallery/imagegellery_images.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    title = models.CharField(max_length=150, verbose_name='Мета-заголовок', blank=True, null=True)
    metadescription = models.TextField(blank=True, null=True, verbose_name='Мета-описание')
    propertytitle = models.CharField(verbose_name="Мета-заголовок ссылки", max_length=150, blank=True, null=True,)
    propertydescription = models.CharField(verbose_name="Мета-описание ссылки", max_length=255, blank=True, null=True,)
    slug = models.SlugField(max_length=140, unique=True)
    cover = models.FileField("Обложка", upload_to="blogs/%Y/%m/%d/", blank=True, null=True, default='default/blogs/cover.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    image = models.FileField("Изображение", upload_to="blogs/%Y/%m/%d/", blank=True, null=True, default='default/blogs/cover.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    publishet = models.BooleanField("Опубликован", default=False)
    create = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.name


    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"