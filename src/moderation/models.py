from decimal import Decimal
from django.apps import apps      # <-- вот это нужно

from django.core.files.base import ContentFile
from django.db import models
from django.conf import settings
import os
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator, MaxValueValidator

from useraccount.models import Profile


class Advertpayment(models.Model):
    # Основные
    name = models.CharField("Название", max_length=255)
    car_brand = models.ForeignKey('CarBrand', on_delete=models.CASCADE, null=True, blank=True)
    car_model = models.ForeignKey('CarModel', on_delete=models.CASCADE, null=True, blank=True)

    brand = models.CharField("марка", max_length=255, null=True, blank=True)
    model_auto = models.CharField("модель", max_length=255, null=True, blank=True)
    link = models.URLField("Ссылка", max_length=500)
    original_link = models.URLField("Оригинальная ссылка", max_length=500, blank=True, null=True)
    price = models.IntegerField("Стоимость")
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

    )
    published = models.BooleanField("Опубликовано", default=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

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
        GAS = "gas", "Газ / LPG / CNG"

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
        verbose_name = "Купленное"
        verbose_name_plural = "Купленные"



    def __str__(self):
        return self.name



class Currencys(models.Model):
    code = models.CharField("Код валюты", max_length=10, unique=True)  # USD, EUR, KZT
    name = models.CharField("Название", max_length=50)
    rate_to_base = models.DecimalField("Курс к базовой валюте", max_digits=20, decimal_places=6)  # курс относительно базовой валюты

    class Meta:
        verbose_name = "Валюта"
        verbose_name_plural = "Валюты"

    def __str__(self):
        return self.code


class Advert(models.Model):
    # Основные
    name = models.CharField("Название", max_length=255, db_index=True)
    car_brand = models.ForeignKey(
        'CarBrand',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='adverts'
    )
    car_model = models.ForeignKey(
        'CarModel',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='adverts'
    )
    brand = models.CharField("марка", max_length=255, null=True, blank=True, db_index=True)
    model_auto = models.CharField("модель", max_length=255, null=True, blank=True, db_index=True)
    link = models.URLField("Ссылка", max_length=500)
    original_link = models.URLField("Оригинальная ссылка", max_length=500, blank=True, null=True, unique=True)
    price = models.IntegerField("Стоимость", db_index=True)
    currency = models.CharField("Валюта", max_length=10, db_index=True)  # например, 'USD', 'EUR', 'KZT'

    description = models.TextField("Описание", blank=True, null=True)
    images = models.JSONField("Список ссылок на изображения", blank=True, null=True)  # list[str]
    subtitle = models.CharField("Подзаголовок", max_length=255, blank=True, null=True)
    article = models.CharField("Артикул", max_length=500, blank=True, null=True)
    address = models.CharField('Адрес', max_length=500, blank=True, null=True)

    # Характеристики авто
    mileage = models.PositiveIntegerField("Километраж (км)", blank=True, null=True, db_index=True)
    color = models.CharField("Цвет", max_length=150, blank=True, null=True, db_index=True)
    doors = models.PositiveSmallIntegerField("Количество дверей", blank=True, null=True, db_index=True)

    power = models.PositiveIntegerField("Мощность (л.с.)", blank=True, null=True, db_index=True)
    engine_volume = models.DecimalField(
        "Объём двигателя (л)",
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        db_index=True,
    )
    year = models.PositiveSmallIntegerField(
        "Год выпуска",
        blank=True,
        null=True,
        db_index=True,
    )
    published = models.BooleanField("Опубликовано", default=True, db_index=True)
    image_no = models.BooleanField("Не имеет изображения", default=True, db_index=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class TransmissionType(models.TextChoices):
        MANUAL = "manual", "Механика"
        AUTOMATIC = "automatic", "Автомат"
        CVT = "cvt", "Вариатор"
        ROBOT = "robot", "Робот"

    transmission = models.CharField(
        "Коробка передач",
        max_length=20,
        choices=TransmissionType.choices,
        blank=True,
        null=True,
        db_index=True,
    )

    class FuelType(models.TextChoices):
        GASOLINE = "gasoline", "Бензин"
        DIESEL = "diesel", "Дизель"
        ELECTRIC = "electric", "Электро"
        HYBRID = "hybrid", "Гибрид"
        GAS = "gas", "Газ / LPG / CNG"

    fuel = models.CharField(
        "Топливо",
        max_length=20,
        choices=FuelType.choices,
        blank=True,
        null=True,
        db_index=True,
    )

    class DriveType(models.TextChoices):
        FWD = "fwd", "Передний"
        RWD = "rwd", "Задний"
        AWD = "awd", "Полный"

    drive = models.CharField(
        "Привод",
        max_length=10,
        choices=DriveType.choices,
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        indexes = [
            models.Index(fields=['brand', 'model_auto']),
            models.Index(fields=['price', 'created_at']),
            models.Index(fields=['year', 'created_at']),
            models.Index(fields=['mileage', 'created_at']),
        ]
        ordering = ['-car_model__pagetype', '-created_at']

    def clean_fields(self, exclude=None):
        """Очистка полей перед валидацией"""
        super().clean_fields(exclude=exclude)

        # Заменяем * и / на пробелы в текстовых полях
        text_fields = ['name', 'brand', 'model_auto', 'description', 'subtitle', 'address', 'color']

        for field_name in text_fields:
            current_value = getattr(self, field_name)
            if current_value:
                cleaned_value = current_value.replace('*', ' ').replace('/', ' ')
                setattr(self, field_name, cleaned_value)

    def save(self, *args, **kwargs):
        # Очищаем поля от * и / перед сохранением
        self.clean_fields()

        # ⚠️ Печать убрал бы в проде — сильно тормозит при массовых сохранениях
        # print(f"=== СОХРАНЕНИЕ ОБЪЯВЛЕНИЯ ===")
        # ...

        # Автоматический поиск марки и модели из названия
        self.find_brand_and_model_from_first_words()

        # Автоматическое заполнение brand и model_auto из связанных объектов
        if self.car_brand:
            self.brand = self.car_brand.name
        else:
            self.brand = None

        if self.car_model:
            self.model_auto = self.car_model.name
        else:
            self.model_auto = None

        # Исправленная логика для doors
        if self.doors:
            if self.doors > 5:
                self.doors = 5
        elif self.doors is None:
            self.doors = 5

        super().save(*args, **kwargs)

    def find_brand_and_model_from_first_words(self):
        """
        Поиск марки и модели по первым двум словам названия
        Первое слово - марка, второе слово - модель
        """
        if not self.name:
            return

        # ⚠️ импорт локально, чтобы избежать циклических импортов
        from .models import CarBrand, CarModel

        words = self.name.strip().split()
        if len(words) < 2:
            return

        first_word = words[0].strip().lower()
        second_word = words[1].strip().lower()

        found_brand = None
        found_model = None

        # Ищем марку по первому слову
        brand = CarBrand.objects.filter(name__iexact=first_word).first()
        if brand:
            found_brand = brand

            # Ищем модель по второму слову для найденной марки
            model = CarModel.objects.filter(
                brand=brand,
                name__iexact=second_word
            ).first()

            if model:
                found_model = model
            else:
                # Попробуем найти модель по частичному совпадению
                models_qs = CarModel.objects.filter(brand=brand)
                second_lower = second_word.lower()
                for m in models_qs:
                    if second_lower in m.name.lower():
                        found_model = m
                        break
        else:
            # Попробуем найти марку по частичному совпадению
            brands = CarBrand.objects.all()
            for b in brands:
                if first_word in b.name.lower():
                    found_brand = b
                    # Ищем модель для найденной марки
                    model = CarModel.objects.filter(
                        brand=b,
                        name__iexact=second_word
                    ).first()
                    if model:
                        found_model = model
                    break

        # Устанавливаем найденные значения
        if found_brand:
            self.car_brand = found_brand
        if found_model:
            self.car_model = found_model

    def delete_if_old(self, hours_threshold=5):
        """
        Удаляет объект если он не обновлялся более указанного количества часов
        """
        from django.utils import timezone
        from datetime import timedelta

        if timezone.now() - self.updated_at > timedelta(hours=hours_threshold):
            self.delete()
            return True
        return False

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

    type = models.IntegerField(blank=True, null=True)

    document_type = models.CharField(
        "Тип документа",
        max_length=20,
        choices=DocumentType.choices
    )

    update_data = models.DateTimeField(verbose_name='Дата обновления', auto_now=True)
    name = models.CharField(max_length=50, verbose_name='имя')
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Документ заявки"
        verbose_name_plural = "Документы заявки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.aplication.advert}"

    def save(self, *args, **kwargs):
        # Если файла нет, заполнить его из SettingsGlobale
        if not self.file or not self.file.name:
            try:
                from webmain.models import SettingsGlobale  # скорректируйте путь, если нужно
            except Exception:
                SettingsGlobale = None

            if SettingsGlobale:
                settings = SettingsGlobale.objects.first()
                if settings:
                    # найти первый непустой файл в document_file_1..document_file_8
                    default_file = None
                    for idx in range(1, 9):
                        f = getattr(settings, f"document_file_{idx}", None)
                        if f and getattr(f, "name", ""):
                            default_file = f
                            break

                    if default_file:
                        # считать содержимое и записать в поле file
                        try:
                            with default_file.open("rb") as fp:
                                content = fp.read()
                                self.file.save(os.path.basename(default_file.name), ContentFile(content), save=False)
                        except Exception:
                            pass  # тут можно добавить логирование

        super().save(*args, **kwargs)


class CarBrand(models.Model):
    """Марка автомобиля"""
    name = models.CharField(max_length=100, verbose_name="Название марки")

    class Meta:
        verbose_name = "Марка автомобиля"
        verbose_name_plural = "Марки автомобилей"
        ordering = ['name']

    def __str__(self):
        return self.name


class CarModel(models.Model):
    """Модель автомобиля"""
    name = models.CharField(max_length=100, verbose_name="Название модели")
    brand = models.ForeignKey(
        CarBrand,
        on_delete=models.CASCADE,
        verbose_name="Марка автомобиля",
        related_name="models"  # позволяет получать все модели марки через brand.models.all()
    )
    PAGE_CHOICE = [
        (1, 'Легковая'),
        (2, 'Грузовая'),
    ]
    pagetype = models.PositiveSmallIntegerField('Тип', choices=PAGE_CHOICE, blank=False, default=1)

    class Meta:
        verbose_name = "Модель автомобиля"
        verbose_name_plural = "Модели автомобилей"
        ordering = ['brand__name', 'name']
        # Запрещаем дублирование моделей в рамках одной марки
        unique_together = ['brand', 'name']

    def __str__(self):
        return f"{self.brand.name} {self.name}"



class ExpenseMask(models.Model):
    """Справочник статей расходов (маски / шаблоны)"""
    name = models.CharField("Название статьи", max_length=150, unique=True)

    class Meta:
        verbose_name = "Маска статьи расхода"
        verbose_name_plural = "Маски статей расходов"
        ordering = ["name"]

    def __str__(self):
        return self.name


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', related_name='expense_user', null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Расход по заявке"
        verbose_name_plural = "Расходы по заявкам"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.title} — {self.amount} "

class AdvertApplicationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        'AdvertAplication',
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Заявка"
    )
    related_model = models.CharField("Модель", max_length=255)
    related_object_id = models.CharField("ID объекта", max_length=255)
    action = models.CharField("Действие", max_length=50)  # create, update, delete
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Пользователь"
    )
    changes = models.JSONField("Изменения", blank=True, null=True)  # опционально
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лог заявки"
        verbose_name_plural = "Логи заявок"


class AdvertAplication(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В обработке"
        DONE = "done", "Завершена"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    price = models.DecimalField("Стоимость", max_digits=12, decimal_places=2, blank=True, null=True)
    delevery_price = models.DecimalField("Стоимость доставки", max_digits=12, decimal_places=2, blank=True, null=True)

    balance = models.DecimalField(
        "Баланс",
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        default=0,
    )
    current_balance = models.DecimalField(
        "Текущий баланс",
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        default=0,
    )
    # 🔁 БЫЛО: expenses = models.DecimalField(...)
    expenses_total = models.DecimalField(
        "Расходы",
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        default=0,
    )

    order_number = models.CharField(
        "Номер заказа",
        max_length=10,
        blank=True,
        null=True,
        editable=False,
    )

    user = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        related_name="advert_requests",
        blank=True,
    )
    user_menager = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Менеджеры",
        related_name="advert_menager",
        blank=True,
    )
    user_drivers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Водители",
        related_name="advert_drivers",
        blank=True,
    )

    advert_id = models.CharField("ID объявления (во внешней БД)", db_index=True, max_length=20)
    advert_name = models.CharField("Название объявления", max_length=255, blank=True, null=True)

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    # ====== служебные методы ======

    def generate_order_number(self):
        """Генерирует номер заказа в формате 0000001"""
        last_order = (
            AdvertAplication.objects.filter(order_number__isnull=False)
            .exclude(order_number="")
            .order_by("order_number")
            .last()
        )

        if last_order and last_order.order_number:
            try:
                last_number = int(last_order.order_number)
                new_number = last_number + 1
            except (ValueError, TypeError):
                new_number = 1
        else:
            new_number = 1

        return str(new_number).zfill(7)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def get_advert(self):
        Advert = apps.get_model("moderation", "Advert")
        try:
            return Advert.objects.using("adverts").get(id=self.advert_id)
        except Advert.DoesNotExist:
            return None

    def sync_users_from_managers_and_drivers(self):
        """Синхронизирует поле user с user_menager и user_drivers"""
        managers_and_drivers = set(self.user_menager.all()) | set(self.user_drivers.all())
        current_users = set(self.user.all())

        users_to_add = managers_and_drivers - current_users

        # old_managers / old_drivers нужно где-то задавать, тут их нет – если они не нужны, можно убрать логику удаления
        # users_to_remove = ...

        if users_to_add:
            self.user.add(*users_to_add)
            print(f"Добавлены пользователи в user: {[str(u) for u in users_to_add]}")

    def update_cart_vod_for_drivers(self):
        """Обновляет CartVod только для новых водителей"""
        from cart.models import CartVod  # импорт локально

        current_drivers = set(self.user_drivers.all())
        existing_cart_vods = CartVod.objects.filter(application=self)
        existing_drivers = set(cart.voditel for cart in existing_cart_vods)

        drivers_to_add = current_drivers - existing_drivers
        drivers_to_remove = existing_drivers - current_drivers

        for driver in drivers_to_add:
            CartVod.objects.create(
                voditel=driver,
                application=self,
                summa=Decimal("0.01"),
            )

        if drivers_to_remove:
            CartVod.objects.filter(
                application=self,
                voditel__in=drivers_to_remove,
            ).delete()

    class Meta:
        verbose_name = "Заявка на объявление"
        verbose_name_plural = "Заявки на объявления"
        ordering = ["-created_at"]

    def __str__(self):
        users = self.user.all()
        user_str = users[0].username if users.exists() else "нет пользователя"

        # пытаемся взять имя объявления: сначала локальное поле, потом – из внешней БД
        advert_title = self.advert_name
        if not advert_title:
            advert_obj = self.get_advert()
            advert_title = advert_obj.name if advert_obj else "нет объявления"

        return f"Заявка #{self.order_number} от {user_str} на {advert_title}"

class CartVod(models.Model):
    """
    Модель корзины водителя для учета выплат за выполнение заявок.
    Связывает водителя, заявку и сумму выплаты.
    """

    voditel = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        verbose_name='Водитель',
        related_name='driver_carts',
        help_text='Водитель, выполняющий заявку'
    )

    application = models.ForeignKey(
        'moderation.AdvertAplication',
        on_delete=models.CASCADE,
        verbose_name='Заявка',
        related_name='driver_payments',
        help_text='Заявка, за которую производится выплата'
    )

    summa = models.DecimalField(
        verbose_name='Сумма выплаты',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],  # Разрешаем 0
        default=0.00,
        help_text='Сумма к выплате водителю'
    )

    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
        help_text='Время создания записи о выплате'
    )

    updated_at = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True,
        help_text='Время последнего обновления записи'
    )

    class Meta:
        verbose_name = 'Выплата водителю'
        verbose_name_plural = 'Выплаты водителям'
        db_table = 'driver_carts'
        unique_together = ['voditel', 'application']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['voditel', 'created_at']),
            models.Index(fields=['application']),
        ]

    def __str__(self):
        return f"{self.voditel} - {self.summa} руб. ({self.application})"

    @property
    def formatted_summa(self):
        """Форматированная сумма с разделителями"""
        return f"{self.summa:,.2f} руб."

    @classmethod
    def get_driver_total(cls, driver):
        """Общая сумма выплат водителю"""
        return cls.objects.filter(voditel=driver).aggregate(
            total=models.Sum('summa')
        )['total'] or Decimal('0.00')

    @classmethod
    def get_application_payments(cls, application):
        """Все выплаты по конкретной заявке"""
        return cls.objects.filter(application=application).select_related('voditel')


class DriverLocation(models.Model):
    application = models.ForeignKey(
        'AdvertAplication',
        on_delete=models.CASCADE,
        related_name='driver_locations'
    )
    driver = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        limit_choices_to={'employee': 3}  # только водители
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True)  # точность в метрах
    speed = models.FloatField(null=True, blank=True)  # скорость км/ч
    timestamp = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['application', 'driver', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.driver} - {self.timestamp}"


class AdvertAplicationGalleryGroup(models.Model):
    """
    Группа (альбом) медиа-файлов внутри заявки
    Например: 'Доставка', 'Отгрузка', 'Склад', …
    """

    application = models.ForeignKey(
        AdvertAplication,
        on_delete=models.CASCADE,
        related_name="gallery_groups"
    )
    title = models.CharField("Название группы", max_length=120)
    description = models.TextField("Описание группы", blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "Группа медиа"
        verbose_name_plural = "Группы медиа"

    def __str__(self):
        return f"{self.title} — {self.application}"


class AdvertAplicationGallery(models.Model):
    """Фото/видео-отчёты"""
    application = models.ForeignKey(
        AdvertAplication,
        on_delete=models.CASCADE,
        related_name="gallery"
    )
    PAGE_CHOICE = [
        (0, 'Фото-отчет'),
        (1, 'Видео-отчет'),
        (2, 'Билет'),
        (3, 'Чек'),
    ]
    pagetype = models.PositiveSmallIntegerField('Тип', choices=PAGE_CHOICE, blank=False, default=1)

    group = models.ForeignKey(
        AdvertAplicationGalleryGroup,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="items",
        help_text="Можно прикрепить к альбому"
    )
    file = models.FileField(
        upload_to="advert_gallery/",
        help_text="Фото или видео"
    )
    description = models.CharField(
        "Описание файла",
        max_length=255,
        blank=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="uploaded_gallery"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.application} | {self.file.name}"

    @property
    def is_image(self):
        return self.file.name.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp")
        )

    @property
    def is_video(self):
        return self.file.name.lower().endswith(
            (".mp4", ".mov", ".webm", ".mkv")
        )

class Withdrawal(models.Model):
    """Выплаты"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', on_delete=models.CASCADE)
    amount = models.IntegerField("Сумма", blank=True, null=True)
    TYPE_CHOICES = [
        (0, 'Пополнение'),
        (1, 'Списание'),
    ]
    type = models.SmallIntegerField(verbose_name="Пополнение/Списание", choices=TYPE_CHOICES, default=0)
    create = models.DateTimeField(auto_now_add=True)
    application = models.ForeignKey(AdvertAplication, on_delete=models.CASCADE, related_name='withdrawal')

    class Meta:
        verbose_name = "Выплата"
        verbose_name_plural = "Выплаты"

class AdvertApplicationImage(models.Model):
    application = models.ForeignKey(
        AdvertAplication,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='advert_applications/')

class CallSession(models.Model):
    application = models.ForeignKey(AdvertAplication, on_delete=models.CASCADE)
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='calls_made', on_delete=models.CASCADE)
    callee = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='calls_received', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    caller_offer = models.TextField(null=True, blank=True)
    callee_answer = models.TextField(null=True, blank=True)
    caller_ice_candidates = models.TextField(default='[]')
    callee_ice_candidates = models.TextField(default='[]')
    created_at = models.DateTimeField(auto_now_add=True)

    def delete_call(self):
        """Удаляет звонок и связанные данные"""
        self.is_active = False
        self.save()
        # Дополнительная логика очистки, если нужна
        # self.delete()  # если нужно полностью удалить запись


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
    timestamp = models.DateTimeField(auto_now_add=True,null=True)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ['-date']


class WalletDriver(models.Model):
    aplication = models.ForeignKey(
        AdvertAplication,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name="Заявка",
        related_name="driver_wallets",
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Водитель",
        on_delete=models.CASCADE,
        related_name="wallets",
    )

    # 💰 Деньги
    balance = models.DecimalField(
        "Баланс",
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    spent = models.DecimalField(
        "Израсходовано",
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    remainder = models.DecimalField(
        "Остаток",
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    class Meta:
        verbose_name = "Кошелек водителя"
        verbose_name_plural = "Кошельки водителей"

    def __str__(self):
        return f"Кошелёк {self.responsible} по заявке {self.aplication_id}"

    def recalc_remainder(self):
        """Пересчитать остаток = баланс - израсходовано."""
        bal = self.balance or Decimal("0")
        sp = self.spent or Decimal("0")
        self.remainder = bal - sp

    def save(self, *args, **kwargs):
        # перед сохранением всегда синхронизируем остаток
        self.recalc_remainder()
        super().save(*args, **kwargs)


class Path(models.Model):
    STATUS_CHOICES = [
        (0, 'В ожидании'),
        (1, 'Принял'),
        (2, 'Закончил'),
    ]
    status = models.SmallIntegerField(verbose_name="Статус", choices=STATUS_CHOICES, default=0,  editable=False)
    aplication = models.ForeignKey(AdvertAplication,blank=True,null=True, on_delete=models.CASCADE)
    longitude = models.FloatField(verbose_name='Долгота', blank=True, null=True)
    latitude = models.FloatField(verbose_name='Широта', blank=True, null=True)
    name = models.CharField(max_length=100,verbose_name='Название этапа')
    description = models.TextField("Описание", blank=True, null=True)
    request = models.CharField(max_length=255, verbose_name='Заявка')
    responsible = models.ForeignKey(Profile, verbose_name='Ответственный',on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"Path {self.name} ({self.latitude}, {self.longitude})"


class PathResponsibility(models.Model):

    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('accepted', 'Принял'),
        ('completed', 'Закончил'),
    ]

    path_choice = models.ForeignKey(Path, on_delete=models.CASCADE, verbose_name='Путь выбор пути')
    status = models.CharField(max_length=50, verbose_name='Статус', choices=STATUS_CHOICES,)
    additional = models.TextField(verbose_name='Дополнение', blank=True, null=True)
    responsible = models.ForeignKey(Profile, verbose_name='Ответственный',on_delete=models.CASCADE)

    def __str__(self):
        return f"Responsibility for {self.path_choice} assigned to {self.responsible}"


    class Meta:
        verbose_name = "Этап"
        verbose_name_plural = "Этапы"








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