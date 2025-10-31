from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import (FileExtensionValidator)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid
from uuid import uuid4
from moderation.tasks import upload_to_drive_and_delete


def get_user_dir(instance, filename):
    """
    Генерирует путь для сохранения файлов пользователя
    """
    print(f"get_user_dir called: instance={instance}, filename={filename}")

    # Получаем расширение файла
    ext = filename.split('.')[-1]

    # Создаем уникальное имя
    unique_id = uuid.uuid4().hex[:8]
    new_filename = f"{unique_id}_{filename}"

    # Определяем тип файла
    if hasattr(instance, 'avatar') and instance.avatar and instance.avatar.name == filename:
        file_type = 'avatar'
    elif hasattr(instance,
                 'passport_image_1') and instance.passport_image_1 and instance.passport_image_1.name == filename:
        file_type = 'passport_front'
    elif hasattr(instance,
                 'passport_image_2') and instance.passport_image_2 and instance.passport_image_2.name == filename:
        file_type = 'passport_back'
    else:
        file_type = 'other'

    path = f"users/user_{instance.id}/{file_type}/{new_filename}"
    print(f"Generated path: {path}")
    return path

class Profile(AbstractUser):
    """Персона"""
    GENDER_CHOICE = [
        (1, 'Мужской'),
        (2, 'Женский'),
    ]
    TYPE = [
        (0, 'Сотрудники'),
        (1, 'Клиент'),
    ]
    type = models.PositiveSmallIntegerField('Тип пользователя', choices=TYPE, blank=False, default=1)
    EMPLOYEE = [
        (0, 'Нет должности'),
        (1, 'Водитель'),
        (2, 'Менеджер'),
        (3, 'Посредник'),
        (4, 'Админ'),
    ]
    on_hands = models.DecimalField("Стоимость доставки", max_digits=12, decimal_places=2,blank=True,null=True)
    employee = models.PositiveSmallIntegerField('Должность', choices=EMPLOYEE, blank=False, default=0)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(blank=True, verbose_name='Телефон', max_length=500, null=True)
    avatar = models.FileField(upload_to=get_user_dir, blank=True, verbose_name='Аватар', default='default/user-nophoto.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    gender = models.PositiveSmallIntegerField('Пол', choices=GENDER_CHOICE, blank=False, default=1)
    birthday = models.DateField(verbose_name='Дата рождения', blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, verbose_name='Город',null=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Отчество')
    online = models.BooleanField(default=False, verbose_name="Онлайн")
    blocked = models.BooleanField(default=False, verbose_name="Заблокирован")
    deleted = models.BooleanField(default=False, verbose_name="Удален")
    balance = models.PositiveSmallIntegerField(verbose_name='Баланс', default='0')
    device_token = models.TextField(blank=True, null=True, verbose_name="FCM токен устройства")
    listen = models.BooleanField(default=False, verbose_name="Слушать")
    position = models.PositiveSmallIntegerField('Позиция', blank=False, null=True)

    """Паспортные данные пользователя"""
    passport_issued_by_whom = models.TextField("Кем выдан", blank=True, null=True)
    passport_date_of_issue = models.DateField(verbose_name='Дата выдачи', blank=True, null=True)
    passport_the_sub_division_code = models.CharField(max_length=100, blank=True, verbose_name='Код подрозделения',null=True)
    passport_series_and_number = models.CharField(max_length=100, blank=True, verbose_name='Серия и номер',null=True)
    passport_place_of_birth = models.TextField("Место рождения", blank=True, null=True)
    passport_registration = models.TextField("Прописка", blank=True, null=True)
    passport_image_1 = models.FileField(upload_to=get_user_dir, blank=True, verbose_name='Лицевая часть', default='default/user-nophoto.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    passport_image_2 = models.FileField(upload_to=get_user_dir, blank=True, verbose_name='Место прописки', default='default/user-nophoto.png', validators=[FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])],)
    """Данные по организации"""
    company_name = models.CharField(max_length=100, blank=True, verbose_name='Название организации',null=True)

    company_director = models.CharField(max_length=100, blank=True, verbose_name='Руководитель',null=True)
    company_address = models.CharField(max_length=100, blank=True, verbose_name='Юридический адрес',null=True)
    company_nalogovaya = models.CharField(max_length=100, blank=True, verbose_name='Налоговый орган',null=True)
    company_ogrn = models.CharField(max_length=100, blank=True, verbose_name='ОГРН',null=True)
    company_inn = models.CharField(max_length=100, blank=True, verbose_name='ИНН',null=True)
    company_kpp = models.CharField(max_length=100, blank=True, verbose_name='КПП',null=True)
    company_data_registration = models.DateField(verbose_name='Дата регистрации', blank=True, null=True)
    company_type_activity = models.TextField("Основной вид деятельности", blank=True, null=True)

    def get_gender_display(self):
        """Метод для отображения полового признака"""
        return dict(self.GENDER_CHOICE).get(self.gender, 'Не указано')

    def get_type_display(self):
        """Метод для отображения типа пользователя"""
        return dict(self.TYPE).get(self.type, 'Не указан')

    def get_employee_display(self):
        """Метод для отображения должности"""
        return dict(self.EMPLOYEE).get(self.employee, 'Не указана')

    def save(self, *args, **kwargs):
        # Убедитесь, что у пользователя есть ID перед сохранением файлов
        creating = self._state.adding

        if creating:
            # Сначала сохраняем без файлов, чтобы получить ID
            temp_files = {}
            for field_name in ['avatar', 'passport_image_1', 'passport_image_2']:
                field = getattr(self, field_name)
                if field and hasattr(field, 'file'):
                    temp_files[field_name] = field
                    setattr(self, field_name, None)

            # Сохраняем для получения ID
            super().save(*args, **kwargs)

            # Теперь сохраняем файлы
            for field_name, file in temp_files.items():
                setattr(self, field_name, file)
            super().save(*args, **kwargs)
        else:
            # Обычное сохранение для существующих записей
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Notification(models.Model):
    """Персона"""
    TYPE = [
        (1, 'Регистрация'),
        (2, 'Покупка'),
        (3, 'Сбросить пароль'),
        (4, 'Поддержка'),
    ]
    type = models.PositiveSmallIntegerField('Тип', unique=True, choices=TYPE, blank=False, default=1)
    STATUS = [
        (1, 'Не прочитан'),
        (2, 'Прочитан'),
    ]
    status = models.PositiveSmallIntegerField("Статус", choices=STATUS, blank=False, default=1)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name='Пользователь',on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={'model__in': ('blogs', 'pages','categorysblogs', 'tagsblogs',)})
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField('Время отправки',auto_now_add=True)
    message = models.TextField()

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомление"


class Dictofone(models.Model):
    """Выплаты"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Пользователь', on_delete=models.CASCADE)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    files = models.FileField(upload_to=get_user_dir, blank=True, verbose_name=' Записи')

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"




class Cards(models.Model):
    STATUS =[
        (1, 'Активная'),
        (2, 'Не активная'),
    ]
    card = models.CharField(verbose_name='Карта', max_length=19)
    date = models.DateTimeField('Дата обновления карты', auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,verbose_name='Пользователь', related_name='cardowner')
    status = models.PositiveSmallIntegerField("Статус", default=2, choices=STATUS, blank=False)

    def str(self):
        return f'{self.card}'

    def save(self, *args, **kwargs):
        self.card = self.card.replace("-", "")
        formatted_card = '-'.join([self.card[i:i + 4] for i in range(0, len(self.card), 4)])
        self.card = formatted_card
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Банковская карта"
        verbose_name_plural = "Банковские карты"

class PersonalCards(models.Model):
    STATUS =[
        (1, 'Активная'),
        (2, 'Не активная'),
    ]
    TYPE =[
        (1, 'Стандарт'),
        (2, 'Професиональная'),
        (3, 'Вип'),
    ]
    card = models.CharField(verbose_name='Карта', max_length=19)
    discount = models.CharField(verbose_name='Скидка', max_length=19)
    date = models.DateTimeField('Дата обновления карты', auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,verbose_name='Пользователь')
    status = models.PositiveSmallIntegerField("Статус", default=2, choices=STATUS, blank=False)
    type = models.PositiveSmallIntegerField("Тип", default=1, choices=TYPE, blank=False)

    def str(self):
        return f'{self.card}'


    class Meta:
        verbose_name = "Личная карта"
        verbose_name_plural = "Личные карты"

class Bookmark(models.Model):
    """Закладка"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name='Пользователь',on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, verbose_name='Название',null=True)
    information = models.TextField()

    class Meta:
        verbose_name = "Закладка"
        verbose_name_plural = "Закладки"


class Record(models.Model):
    audio = models.FileField(upload_to='audio/', name='audio')
    user = models.ForeignKey('Profile', models.CASCADE, name='user')
    uploaded = models.BooleanField(default=False)  # Добавим флаг для отслеживания
    created_at = models.DateTimeField(null=True,blank=True,auto_now_add=True)

    class Meta:
        verbose_name = "Прослушка"
        verbose_name_plural = "Прослушки"

    def save(self, *args, **kwargs):
        # Если это новая запись и еще не загружена
        super().save(*args, **kwargs)
        user_records = Record.objects.filter(user=self.user).order_by('created_at')
        first_user = user_records.first()
        print(first_user.uploaded,first_user.audio)
        if  len(user_records) > 1:
            if  first_user.uploaded != True and first_user.audio:
                # Запускаем задачу асинхронно
                id = first_user.id
                upload_to_drive_and_delete(id)

