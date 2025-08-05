from ckeditor.fields import RichTextField
from django import forms
from django.forms import Textarea
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from slugify import slugify
import json
from django.core.validators import FileExtensionValidator
from multiupload.fields import MultiFileField
from ckeditor.widgets import CKEditorWidget
from django_ace import AceWidget
from django.contrib.auth import get_user_model


from .models import TicketComment, Notificationgroups, Ticket
from webmain.models import SettingsGlobale, HomePage, AboutPage, ContactPage, Faqs, Blogs, CategorysBlogs, TagsBlogs, Pages, Seo
from useraccount.models import  Notification, Withdrawal


class TicketCommentForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Написать комментарий'}))
    files = MultiFileField(required=False, max_num=10, attrs={'class': 'form-control cursor-pointer form-file'})

    class Meta:
        model = TicketComment
        fields = ['content', 'files']


    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files:
            for file in files:
                try:
                    FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])(file)
                except forms.ValidationError:
                    self.add_error('files', f"Файл '{file.name}' имеет недопустимое расширение.")
        return files



class SettingsGlobaleForm(forms.ModelForm):
    logo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'general_logo'}))
    doplogo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'doplogo'}))
    logo_white = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'general_logo_white'}))
    doplogo_white = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'doplogo_white'}))
    favicon = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'favicon'}))
    paymentmethod = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'paymentmethod'}))
    name = forms.CharField(required=True, max_length=256, widget=forms.TextInput(attrs={'placeholder': 'Название', 'id': 'global_name', 'class': 'form-control input-default '}))
    content = forms.CharField(max_length=256, required=False, widget=forms.Textarea(attrs={'placeholder': 'Копирайт', 'class': 'form-control input-default '}),)
    description = forms.CharField(widget=CKEditorWidget(),)
    message_header = forms.CharField(widget=AceWidget(mode='html', width="100%", height="500px", readonly=False, behaviours=True, showgutter=True,  wordwrap=False, usesofttabs=True))
    message_footer = forms.CharField(widget=AceWidget(mode='html', width="100%", height="500px", readonly=False, behaviours=True, showgutter=True,  wordwrap=False, usesofttabs=True))
    yandex_metrica = forms.CharField(max_length=1024, required=False, widget=forms.Textarea(attrs={'placeholder': 'Яндекс Метрика', 'class': 'form-control input-default '}),)
    google_analitic = forms.CharField(max_length=1024, required=False, widget=forms.Textarea(attrs={'placeholder': 'Google Аналитика', 'class': 'form-control input-default '}),)
    price = forms.CharField(required=True, max_length=256, widget=forms.TextInput(attrs={'placeholder': 'Стоимость за километр', 'id': 'global_price', 'class': 'form-control input-default '}))
    commission = forms.CharField(required=True, max_length=256, widget=forms.TextInput(attrs={'placeholder': 'Размер комиссии', 'id': 'global_commission', 'class': 'form-control input-default '}))
    email_host = forms.CharField(max_length=256, required=False, widget=forms.TextInput(attrs={'placeholder': 'Email Site HOST', 'class': 'form-control input-default '}))
    default_from_email = forms.CharField(max_length=256, required=False, widget=forms.TextInput(attrs={'placeholder': 'Email Site From', 'class': 'form-control input-default '}))
    email_port = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={'placeholder': 'Email Site PORT', 'class': 'form-control input-default '}))
    email_host_user = forms.CharField(max_length=256, required=False, widget=forms.TextInput(attrs={'placeholder': 'Email Site User', 'class': 'form-control input-default '}))
    email_host_password = forms.CharField(max_length=256, required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Email Site Password', 'class': 'form-control input-default '}))
    email_use_tls = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), initial=False)
    email_use_ssl = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), initial=False)

    class Meta:
        model = SettingsGlobale
        fields = [
            'logo', 'price', 'doplogo', 'logo_white','doplogo_white','favicon', 'paymentmethod',
            'name', 'description', 'content', 'message_header', 'message_footer', 'yandex_metrica', 'google_analitic', 'commission',
            'email_host', 'default_from_email', 'email_port','email_host_user', 'email_host_password', 'email_use_tls', 'email_use_ssl'
        ]
    def __init__(self, *args, **kwargs):
        super(SettingsGlobaleForm, self).__init__(*args, **kwargs)

class HomepageSetForm(forms.ModelForm):
    # Первый блок
    previev = forms.FileField(required=False,widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'previev'}))
    title = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Мета-заголовок <страницы о проекте>', 'class': 'form-control input-default'}))
    metadescription = forms.CharField(required=False, widget=forms.Textarea(attrs={'placeholder': 'Мета-описание <страницы о проекте>', 'class': 'form-control input-default'}))
    propertytitle = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Мета-заголовок для previev <страницы о проекте>','class': 'form-control input-default'}))
    propertydescription = forms.CharField(required=False, widget=forms.Textarea(attrs={'placeholder': 'Мета-описание для previev <страницы о проекте>', 'class': 'form-control input-default'}))
    text = forms.CharField(required=False, widget=forms.Textarea(attrs={'placeholder': 'Мета-описание для previev <страницы о проекте>', 'class': 'form-control input-default'}))


    class Meta:
        model = HomePage
        fields = [
            'previev', 'title',
            'metadescription','propertytitle','propertydescription','text'
        ]

    def __init__(self, *args, **kwargs):
        super(HomepageSetForm, self).__init__(*args, **kwargs)

class AboutPageForm(forms.ModelForm):
    previev = forms.FileField(required=False,widget=forms.FileInput(attrs={'class': 'form-file-input form-control', 'id': 'previev'}))
    title = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Мета-заголовок <страницы о проекте>', 'class': 'form-control input-default'}))
    metadescription = forms.CharField(required=False, widget=forms.Textarea(attrs={'placeholder': 'Мета-описание <страницы о проекте>', 'class': 'form-control input-default'}))
    propertytitle = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Мета-заголовок для previev <страницы о проекте>','class': 'form-control input-default'}))
    propertydescription = forms.CharField(required=False, widget=forms.Textarea(attrs={'placeholder': 'Мета-описание для previev <страницы о проекте>', 'class': 'form-control input-default'}))
    text = forms.CharField(required=False, widget=forms.Textarea(attrs={'placeholder': 'Мета-описание для previev <страницы о проекте>', 'class': 'form-control input-default'}))


    class Meta:
        model = AboutPage
        fields = '__all__'


class FaqsForm(forms.ModelForm):
    class Meta:
        model = Faqs
        fields = ['question', 'answer']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Введите вопрос'}),
            'answer': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Введите ответ'}),
        }

class BlogsForm(forms.ModelForm):
    category = forms.ModelMultipleChoiceField(
        queryset=CategorysBlogs.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'default-select form-control wide', 'id': 'id_category', 'aria-label': 'Выберите категории' }),
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=TagsBlogs.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'default-select form-control wide', 'id': 'id_category',
                                           'aria-label': 'Выберите Тэг'}),
    )
    publishet = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Черновик'
    )
    class Meta:
        model = Blogs
        fields = ['name', 'description', 'title', 'metadescription', 'author', 'resource',
                  'category', 'slug', 'propertytitle', 'propertydescription',
                  'previev', 'cover', 'publishet']
        widgets = {
            'author': forms.Select(attrs={'class': 'default-select form-control wide', 'placeholder': 'Автор'}),
            'name': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Название'}),
            'resource': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Источник'}),
            'description': forms.CharField(widget=CKEditorWidget(),),
            'title': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Заголовок'}),
            'metadescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Содержимое'}),
            'category': forms.SelectMultiple(attrs={'class': 'default-select form-control wide', 'id': 'id_category', 'aria-label': 'Выберите категории', 'name': 'category' }),
            'slug': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Slug'}),
            'propertytitle': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Заголовок свойства'}),
            'propertydescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Описание свойства'}),
            'previev': forms.FileInput(attrs={'class': 'form-file-input form-control'}),
            'cover': forms.FileInput(attrs={'class': 'form-file-input form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Генерация slug из name с помощью slugify
        instance.slug = slugify(instance.name)  # Используем slugify для генерации slug
        if commit:
            instance.save()
        return instance

class PagesForm(forms.ModelForm):
    class Meta:
        model = Pages
        fields = ['pagetype', 'name', 'description', 'title', 'metadescription', 'slug', 'propertytitle', 'propertydescription', 'previev', 'publishet']
        widgets = {
            'pagetype': forms.Select(attrs={'class': 'default-select form-control wide', 'placeholder': 'Тип страницы'}),
            'name': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Название'}),
            'description': forms.CharField(widget=CKEditorWidget(),),
            'slug': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Slug'}),
            'previev': forms.FileInput(attrs={'class': 'form-file-input form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Заголовок'}),
            'metadescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-описание'}),
            'propertytitle': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-заголовок ссылки'}),
            'propertydescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-описание ссылки'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Генерация slug из name с помощью slugify
        instance.slug = slugify(instance.name)  # Используем slugify для генерации slug
        if commit:
            instance.save()
        return instance

class SeoForm(forms.ModelForm):
    class Meta:
        model = Seo
        fields = ['pagetype', 'previev', 'metadescription', 'title', 'propertytitle', 'propertydescription', 'setting']
        widgets = {
            'pagetype': forms.Select(attrs={'class': 'default-select form-control wide', 'placeholder': 'Тип страницы'}),
            'previev': forms.FileInput(attrs={'class': 'form-file-input form-control'}),

            'setting': forms.Select(attrs={'class': 'default-select form-control wide', 'placeholder': 'Настройка'}),
            'metadescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-описание'}),
            'title': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-заголовок'}),
            'propertytitle': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-заголовок ссылки'}),
            'propertydescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-описание ссылки'}),
        }

class NotificationForm(forms.ModelForm):
    user = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'default-select form-control wide', 'id': 'id_user',
                                           'aria-label': 'Выберите пользователей'}),
    )
    class Meta:
        model = Notificationgroups
        fields = ['content_type', 'user', 'message', 'object_id']
        widgets = {
            'content_type': forms.Select(attrs={'class': 'default-select form-control wide', 'placeholder': 'Тип контента'}),
            'message': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Сообщение'}),
            'object_id': forms.NumberInput(attrs={'class': 'form-control input-default', 'placeholder': 'ID объекта'}),
            'slug': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Slug'}),

        }




class CategorysForm(forms.ModelForm):
    class Meta:
        model = CategorysBlogs
        fields = ['name', 'slug', 'description', 'parent', 'cover', 'icon', 'image','previev', 'title', 'metadescription', 'publishet' ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Название'}),
            'slug': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Slug'}),
            'description': Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Описание'}),
            'title': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Заголовок'}),
            'metadescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-описание'}),
            'propertytitle': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Заголовок'}),
            'propertydescription': forms.Textarea(attrs={'class': 'form-control input-default', 'placeholder': 'Мета-описание'}),
            'parent': forms.Select(attrs={'class': 'default-select form-control wide', 'placeholder': 'Родитель'}),
            'icon': forms.FileInput(attrs={'class': 'form-file-input form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-file-input form-control'}),
            'cover': forms.FileInput(attrs={'class': 'form-file-input form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Генерация slug из name с помощью slugify
        instance.slug = slugify(instance.name)  # Используем slugify для генерации slug
        if commit:
            instance.save()
        return instance

class WithdrawForm(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control input-default', 'placeholder': 'Сумма'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        # Проверка на баланс пользователя
        if self.user:
            balance = float(self.user.balance)
            if amount > balance:
                # Используем форматирование для вывода ошибки без лишней точки
                raise forms.ValidationError(f"Вы не можете списать больше {balance:.2f}.")

        return amount




class TicketWithCommentForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Написать комментарий'}))
    files = MultiFileField(required=False, max_num=10, attrs={'class': 'form-control cursor-pointer form-file'})

    class Meta:
        model = Ticket
        fields = ['themas']
        widgets = {
            'themas': forms.TextInput(attrs={'class': 'form-control input-default', 'placeholder': 'Тема'}),
        }

    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files:
            for file in files:
                try:
                    FileExtensionValidator(allowed_extensions=['png', 'webp', 'jpeg', 'jpg', 'svg'])(file)
                except forms.ValidationError:
                    self.add_error('files', f"Файл '{file.name}' имеет недопустимое расширение.")
        return files