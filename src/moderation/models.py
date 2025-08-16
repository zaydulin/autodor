from django.db import models
from django.conf import settings
import os
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator, MaxValueValidator

class Advert(models.Model):
    # Основные
    name = models.CharField("Название", max_length=255)
    brand = models.CharField("марка", max_length=255)
    model_auto = models.CharField("модель", max_length=255)
    link = models.URLField("Ссылка", max_length=500)
    original_link = models.URLField("Оригинальная ссылка", max_length=500, blank=True, null=True)
    price = models.DecimalField("Стоимость", max_digits=12, decimal_places=2)
    currency = models.CharField("Валюта", max_length=10)  # например, 'USD', 'EUR', 'KZT'
    description = models.TextField("Описание", blank=True, null=True)
    images = models.JSONField("Список ссылок на изображения", blank=True, null=True)  # храним list[str]
    subtitle = models.CharField("Подзаголовок", max_length=255, blank=True, null=True)
    article = models.CharField("Артикул", max_length=100, blank=True, null=True)
    address = models.CharField('Адрес', max_length=100,blank=True,null=True)

    # Характеристики авто
    mileage = models.PositiveIntegerField("Километраж (км)", blank=True, null=True)
    color = models.CharField("Цвет", max_length=50, blank=True, null=True)
    doors = models.PositiveSmallIntegerField("Количество дверей", blank=True, null=True)

    power = models.PositiveIntegerField("Мощность (л.с.)", blank=True, null=True)
    engine_volume = models.DecimalField("Объём двигателя (л)", max_digits=4, decimal_places=1, blank=True, null=True)

    year = models.PositiveSmallIntegerField(
        "Год выпуска",
        blank=True,
        null=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )

    class TransmissionType(models.TextChoices):
        MANUAL = "manual", "Механика"
        AUTOMATIC = "automatic", "Автомат"
        CVT = "cvt", "Вариатор"
        ROBOT = "robot", "Робот"

    transmission = models.CharField(
        "Коробка передач", max_length=20, choices=TransmissionType.choices, blank=True, null=True
    )

    class FuelType(models.TextChoices):
        GASOLINE = "gasoline", "Бензин"
        DIESEL = "diesel", "Дизель"
        ELECTRIC = "electric", "Электро"
        HYBRID = "hybrid", "Гибрид"

    fuel = models.CharField(
        "Топливо", max_length=20, choices=FuelType.choices, blank=True, null=True
    )

    class DriveType(models.TextChoices):
        FWD = "fwd", "Передний"
        RWD = "rwd", "Задний"
        AWD = "awd", "Полный"

    drive = models.CharField(
        "Привод", max_length=10, choices=DriveType.choices, blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"

    def __str__(self):
        return self.name


class AdvertDocument(models.Model):
    class DocumentType(models.TextChoices):
        INVOICE = "invoice", "Накладная"
        CONTRACT = "contract", "Договор"
        CUSTOMS = "customs", "Таможенная"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    aplication = models.ForeignKey(
        "AdvertAplication",
        on_delete=models.CASCADE,
        verbose_name="заявка",
        related_name="documents"
    )

    file = models.FileField(
        "Файл документа",
        upload_to="advert_documents/",
        blank=False,
        null=False
    )

    document_type = models.CharField(
        "Тип документа",
        max_length=20,
        choices=DocumentType.choices
    )
    name = models.CharField(max_length=50,verbose_name='имя')
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Документ заявки"
        verbose_name_plural = "Документы заявки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.aplication.advert}"

# class DocumentInfo(models.Model):
#     advert = models.ForeignKey('Advert',on_delete=models.CASCADE)
#     aplication = models.ForeignKey('AdvertAplication',on_delete=models.CASCADE)
#
class BaseDocument(models.Model):
    name = models.CharField(max_length=100)
    document = models.FileField(upload_to='base_documents')


class AdvertExpense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    aplication = models.ForeignKey(
        "AdvertAplication",
        on_delete=models.CASCADE,
        verbose_name="Объявление",
        related_name="expenses"
    )

    title = models.CharField(
        "Статья расходов",
        max_length=255
    )

    amount = models.DecimalField(
        "Сумма",
        max_digits=12,
        decimal_places=2
    )

    date = models.DateField(
        "Дата расхода"
    )

    created_at = models.DateTimeField(
        "Дата добавления",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Расход по заявке"
        verbose_name_plural = "Расходы по заявкам"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.title} — {self.amount} ({self.aplication.advert.name})"


class AdvertAplication(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В обработке"
        DONE = "done", "Завершена"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price = models.DecimalField("Стоимость", max_digits=12, decimal_places=2)

    user = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        related_name="advert_requests"
    )
    user_menager = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Менеджеры",
        related_name="advert_menager"
    )
    user_drivers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Водители",
        related_name="advert_drivers"
    )

    advert = models.ForeignKey(
        Advert,
        on_delete=models.CASCADE,
        verbose_name="Объявление",
        related_name="requests"
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на объявление"
        verbose_name_plural = "Заявки на объявления"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заявка #{self.id} от {self.user} на {self.advert}"




class CallSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(AdvertAplication, on_delete=models.CASCADE)
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='calls_made', on_delete=models.CASCADE)
    callee = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='calls_received', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    caller_offer = models.TextField(null=True, blank=True)
    callee_answer = models.TextField(null=True, blank=True)
    caller_ice_candidates = models.TextField(default='[]')
    callee_ice_candidates = models.TextField(default='[]')
    created_at = models.DateTimeField(auto_now_add=True)


class ChatMessage(models.Model):
    STATUS_CHOICES = [
        (0, 'Отправлено'),
        (1, 'Прочитано'),
    ]
    status = models.SmallIntegerField(verbose_name="Статус", choices=STATUS_CHOICES, default=1,  editable=False)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applications = models.ForeignKey(AdvertAplication, on_delete=models.CASCADE, verbose_name="Чат", related_name='chatmessage')
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    content = models.TextField(verbose_name="Сообщение")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Автор", blank=True, null=True)
    views = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name='Пользователи', related_name='viewsmessage')

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ['-date']











# Create your models here.
class Stopwords(models.Model):
    """Стоп слова"""
    id = models.AutoField(primary_key=True)
    name = models.CharField("Стоп слова", max_length=120)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Стоп слово"
        verbose_name_plural = "Стоп слова"


class Subscriptions(models.Model):
    """Подписки"""
    email = models.CharField(blank=True, verbose_name='Email', unique=True, max_length=500, null=True)
    create = models.DateTimeField(auto_now=True, blank=True,null=True)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Подписки"
        verbose_name_plural = "Подписки"


class Collaborations(models.Model):
    name = models.TextField(verbose_name='Имя')
    email = models.TextField(verbose_name='Электронная почта')
    subject = models.TextField(verbose_name='Обьект сотрудничества')
    phone = models.TextField(verbose_name='Номер телефона')
    message = models.TextField(verbose_name='Сообщение')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Запрос на сотрудничество"
        verbose_name_plural = "Запросы на сотрудничество"


class Ticket(models.Model):
    date = models.DateTimeField(verbose_name="Дата", auto_now_add=True)
    STATUS_CHOICES = [
        (0, 'Новое'),
        (1, 'Обратная связь'),
        (2, 'В процессе'),
        (3, 'Решенный'),
        (4, 'Закрытый'),

    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.SmallIntegerField(verbose_name="Статус", choices=STATUS_CHOICES, default=0)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Автор",on_delete=models.CASCADE)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="ticket_manager", verbose_name="Менеджер",on_delete=models.CASCADE, null=True, blank=True)
    themas = models.TextField("Тема")

    class Meta:
        verbose_name = "Тикет"
        verbose_name_plural = "Тикеты"
        ordering = ['date']


class TicketComment(models.Model):
    STATUS_CHOICES = [
        (0, 'Заказчик'),
        (1, 'Поддержка'),
    ]
    status = models.SmallIntegerField(verbose_name="Статус", choices=STATUS_CHOICES, default=1,  editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, verbose_name="Ticket", related_name='comments')
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    content = models.TextField(verbose_name="Комментарий")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Автор", blank=True, null=True)

    class Meta:
        verbose_name = "Комментарий тикета"
        verbose_name_plural = "Комментарии тикета"
        ordering = ['-date']


class TicketCommentMedia(models.Model):
    comment = models.ForeignKey('TicketComment', on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='ticket/%Y/%m/%d/tiket_file/')

    def get_file_name(self):
        return os.path.basename(self.file.name)

    class Meta:
        verbose_name = "Файл комментария тикета"
        verbose_name_plural = "Файлы комментариев тикета"

class Notificationgroups(models.Model):
    """Уведомление"""
    user = models.ManyToManyField(settings.AUTH_USER_MODEL,verbose_name='Пользователь')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={'model__in': ('blogs', 'pages','categorysblogs', 'tagsblogs',)})
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField('Время отправки', auto_now_add=True)
    message = models.TextField()
    slug = models.TextField(editable=False)

    class Meta:
        verbose_name = "Груповое уведомление"
        verbose_name_plural = "Груповые уведомления"