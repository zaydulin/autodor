from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, CreateView, UpdateView
from django.contrib.auth import logout, authenticate, login, get_user_model
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.urls import reverse
from django.http import HttpResponseServerError, HttpResponseForbidden, JsonResponse
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetCompleteView, PasswordResetDoneView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
import json
from django.shortcuts import render, get_object_or_404
from django.db import transaction
import base64
from django.core.files.base import ContentFile
from django.db.models import Count
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages


# Models
from webmain.models import Seo
from moderation.models import Ticket, TicketComment, TicketCommentMedia
from useraccount.models import Profile, Notification, Withdrawal, Cards

# Forms
from useraccount.forms import SignUpForm, UserProfileForm, PasswordResetEmailForm, SetPasswordFormCustom, CardsForm
from moderation.forms import TicketCommentForm, WithdrawForm,  TicketWithCommentForm


def custom_logout(request):
    logout(request)
    return redirect('useraccount:login')

"""Регистрация/Авторизация"""

class CustomLoginView(auth_views.LoginView):
    template_name = 'site/useraccount/login.html'

    def get_success_url(self):
        type = self.request.user.type
        if type == 0:
            success_url = reverse('moderation:adverts')
        else:
            success_url = reverse('useraccount:edit_profile')

        return success_url

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            seo_data = Seo.objects.get(pagetype=5)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.description
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None

        return context


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'site/useraccount/signup.html'
    success_url = reverse_lazy('useraccount:login')  # URL для редиректа после успешной регистрации

    def get_success_url(self):
        # Возвращаем success_url, можно переопределить логику, если нужно
        return self.success_url

    def get_form_kwargs(self):
        # Передаем дополнительные аргументы в форму, если требуется
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Убедитесь, что форма поддерживает user
        return kwargs

    def form_valid(self, form):
        # Сохраняем пользователя
        user = form.save()
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')

        # Аутентифицируем пользователя
        user = authenticate(username=username, password=password)
        if user is not None:
            # Входим в систему
            login(self.request, user)
            return redirect(self.get_success_url())
        else:
            # Возвращаем ошибку, если аутентификация не удалась
            return HttpResponseServerError('Ошибка аутентификации')

    def get_context_data(self, **kwargs):
        # Добавляем данные для SEO
        context = super().get_context_data(**kwargs)
        try:
            seo_data = Seo.objects.get(pagetype=6)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.metadescription
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            # Добавляем пустые значения, если SEO данных нет
            context.update({
                'seo_previev': None,
                'seo_title': None,
                'seo_description': None,
                'seo_propertytitle': None,
                'seo_propertydescription': None,
            })
        return context


class CustomPasswordResetView(PasswordResetView):
    template_name = 'site/useraccount/restore_access.html'
    email_template_name = 'site/email/password_reset_email.html'
    subject_template_name = 'site/email/password_reset_subject.txt'
    form_class = PasswordResetEmailForm
    success_url = reverse_lazy('useraccount:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'site/useraccount/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'site/useraccount/restore_access_user.html'
    form_class = SetPasswordFormCustom
    success_url = reverse_lazy('useraccount:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'site/useraccount/password_reset_complete.html'


"""Личный кабинет"""

@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class EditMyProfileView(TemplateView, LoginRequiredMixin):
    template_name = 'site/useraccount/profile_edit.html'

    def get(self, request, *args, **kwargs):
        initial_data = {'birthday': request.user.birthday.strftime('%Y-%m-%d') if request.user.birthday else None}
        form = UserProfileForm(instance=request.user, initial=initial_data)
        password_form = PasswordChangeForm(user=request.user)  # Форма для смены пароля

        context = self.get_context_data(form=form, password_form=password_form, title='Личные данные')
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        password_form = PasswordChangeForm(data=request.POST, user=request.user)  # Форма для смены пароля

        # Обработка данных профиля
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлен успешно.")
        else:
            messages.error(request, "Ошибка при обновлении профиля.")
            print("Form errors:", form.errors)

        # Обработка смены пароля
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Чтобы пользователь не вышел после смены пароля
            messages.success(request, "Пароль изменен успешно.")
        else:
            messages.error(request, "Ошибка при смене пароля.")
            print("Password form errors:", password_form.errors)

        context = self.get_context_data(form=form, password_form=password_form, title='Личные данные')
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # Вызов `super()` сохраняет функциональность
        try:
            seo_data = Seo.objects.get(pagetype=8)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.metadescription
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None
        return context

@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class NotificationView(ListView):
    model = Notification
    template_name = 'site/useraccount/notification_list.html'
    context_object_name = 'notificationes'
    paginate_by = 30

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user).order_by('-created_at')
        print(f"Notifications for user {self.request.user}: {queryset}")
        return queryset

    def get(self, request, *args, **kwargs):
        # Обновляем статус уведомлений перед отображением страницы
        with transaction.atomic():
            updated_rows = Notification.objects.filter(
                user=self.request.user,
                status=1  # Статус "Не прочитан"
            ).update(status=2)  # Меняем на "Прочитан"
        print(
            f"Updated {updated_rows} notifications to read status.")  # Выводим количество обновленных строк для отладки
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            seo_data = Seo.objects.get(pagetype=11)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.description
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None

        print(f"Context data: {context}")  # Выводим контекст для отладки

        return context

"""Тикеты"""
@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class TicketsView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'site/useraccount/tickets.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        ticket = Ticket.objects.order_by('-date').filter(author=user)
        context['statuses'] = Ticket.STATUS_CHOICES

        search_name = self.request.GET.get('search_name', '')
        if search_name:
            ticket = ticket.filter(themas__icontains=search_name)

        search_id = self.request.GET.get('search_id', '')
        if search_id:
            ticket = ticket.filter(id__icontains=search_id)

        search_type = self.request.GET.get('search_type', '')
        if search_type:
            ticket = ticket.filter(status=search_type)

        search_date = self.request.GET.get('search_date', '')
        if search_date:
            # Преобразуем строку даты в объект datetime
            try:
                search_date = timezone.datetime.strptime(search_date, '%Y-%m-%d').date()
                ticket = ticket.filter(date__date=search_date)
            except ValueError:
                pass

        # Пагинация
        paginator = Paginator(ticket, 10)  # 20 элементов на страницу
        page = self.request.GET.get('page')
        try:
            ticket_list = paginator.page(page)
        except PageNotAnInteger:
            ticket_list = paginator.page(1)
        except EmptyPage:
            ticket_list = paginator.page(paginator.num_pages)

        try:
            seo_data = Seo.objects.get(pagetype=6)
            context['seo_previev'] = seo_data.previev
            context['seo_title'] = seo_data.title
            context['seo_description'] = seo_data.description
            context['seo_propertytitle'] = seo_data.propertytitle
            context['seo_propertydescription'] = seo_data.propertydescription
        except Seo.DoesNotExist:
            context['seo_previev'] = None
            context['seo_title'] = None
            context['seo_description'] = None
            context['seo_propertytitle'] = None
            context['seo_propertydescription'] = None

        context['ticket_list'] = ticket_list  # Передаем отфильтрованные задачи
        context['paginator'] = paginator
        context['page_obj'] = ticket_list
        return context


@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketWithCommentForm
    template_name = 'site/useraccount/ticket_form.html'
    context_object_name = 'ticket'

    @transaction.atomic
    def form_valid(self, form):
        ticket = form.save(commit=False)
        ticket.author = self.request.user

        User = get_user_model()
        managers = User.objects.filter(type=2).annotate(ticket_count=Count('ticket_manager'))

        if managers.exists():
            ticket.manager = min(managers, key=lambda x: x.ticket_count)

        ticket.save()

        # Создаем первый комментарий, связанный с тикетом
        comment = TicketComment.objects.create(
            ticket=ticket,
            author=self.request.user,
            content=form.cleaned_data['content']
        )

        files = form.cleaned_data.get('files')
        if files:
            for file in files:
                TicketCommentMedia.objects.create(comment=comment, file=file)

        return redirect(reverse('useraccount:tickets'))

    def form_invalid(self, form):
        print(form.errors)  # Для отладки
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class TicketMessageView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = 'site/useraccount/tickets_messages.html'
    context_object_name = 'ticket'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = self.object

        # Get all comments related to the ticket
        comments = TicketComment.objects.filter(ticket=ticket).prefetch_related('media').all()

        # Setup pagination
        paginator = Paginator(comments, 10)  # Show 10 comments per page
        page = self.request.GET.get('page')

        try:
            comments_paginated = paginator.page(page)
        except PageNotAnInteger:
            comments_paginated = paginator.page(1)
        except EmptyPage:
            comments_paginated = paginator.page(paginator.num_pages)

        context['ticket_comments'] = comments_paginated
        context['form'] = TicketCommentForm()
        context['ticket'] = ticket
        context['paginator'] = paginator
        context['page_obj'] = comments_paginated

        try:
            seo_data = Seo.objects.get(pagetype=6)
            context.update({
                'seo_previev': seo_data.previev,
                'seo_title': seo_data.title,
                'seo_description': seo_data.description,
                'seo_propertytitle': seo_data.propertytitle,
                'seo_propertydescription': seo_data.propertydescription,
            })
        except Seo.DoesNotExist:
            context.update({
                'seo_previev': None,
                'seo_title': None,
                'seo_description': None,
                'seo_propertytitle': None,
                'seo_propertydescription': None,
            })

        return context


@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class TicketDeleteView(LoginRequiredMixin, View):
    success_url = reverse_lazy('useraccount:tickets')

    def post(self, request):
        data = json.loads(request.body)
        ticket_ids = data.get('ticket_ids', [])
        if ticket_ids:
            Ticket.objects.filter(id__in=ticket_ids).delete()
        return JsonResponse({'status': 'success', 'redirect': self.success_url})


@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class TicketCommentCreateView(LoginRequiredMixin, CreateView):
    model = TicketComment
    form_class = TicketCommentForm

    @transaction.atomic
    def form_valid(self, form):
        ticket_id = self.kwargs['ticket_id']
        ticket = get_object_or_404(Ticket, id=ticket_id)
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = self.request.user
        comment.save()

        files = self.request.FILES.getlist('files')
        for file in files:
            TicketCommentMedia.objects.create(comment=comment, file=file)

        return JsonResponse({
            'status': 'success',
            'comment': {
                'id': comment.id,
                'author': comment.author.username,
                'content': comment.content,
                'date': comment.date.strftime('%Y-%m-%d %H:%M:%S'),
                'files': [{'name': media.file.name, 'url': media.file.url} for media in comment.media.all()]
            }
        })

    def form_invalid(self, form):
        print(form.errors)  # Для отладки
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class WithdrawPage(LoginRequiredMixin, TemplateView):
    template_name = 'site/useraccount/withdraw.html'
    model = Withdrawal
    context_object_name = 'withdraw'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        withdraw = Withdrawal.objects.filter(user=user).order_by('-pk')

        search_id = self.request.GET.get('search_id', '')
        if search_id:
            withdraw = withdraw.filter(pk=search_id)

        search_type = self.request.GET.get('search_type', '')
        if search_type:
            withdraw = withdraw.filter(type=search_type)

        search_date = self.request.GET.get('search_date', '')
        if search_date:
            # Преобразуем строку даты в объект datetime
            try:
                search_date = timezone.datetime.strptime(search_date, '%Y-%m-%d').date()
                withdraw = withdraw.filter(create=search_date)
            except ValueError:
                pass

        # Пагинация
        paginator = Paginator(withdraw, 10)
        page = self.request.GET.get('page')
        try:
            withdraw_list = paginator.page(page)
        except PageNotAnInteger:
            withdraw_list = paginator.page(1)
        except EmptyPage:
            withdraw_list = paginator.page(paginator.num_pages)

        context['withdraw_list'] = withdraw_list  # Передаем отфильтрованные задачи
        context['paginator'] = paginator
        context['page_obj'] = withdraw_list
        context['types'] = Withdrawal.TYPE_CHOICES
        context['balance'] = user.balance
        context['cards'] = user.cardowner.first()
        # Добавляем форму вывода
        context['withdraw_form'] = WithdrawForm()
        # Добавляем форму
        context['cards_form'] = CardsForm()
        # Форма для редактирования карты (если карта существует)
        if context['cards']:
            context['edit_cards_form'] = CardsForm(instance=context['cards'])

        return context


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class WithdrawCreateView(CreateView):
    model = Withdrawal
    form_class = WithdrawForm

    def post(self, request, *args, **kwargs):
        # Создаем экземпляр формы с переданными данными
        form = self.form_class(data=request.POST, user=request.user)

        if form.is_valid():
            # Получаем сумму, которую пользователь хочет вывести
            amount = form.cleaned_data['amount']

            # Получаем пользователя
            user = request.user

            # Проверка, что у пользователя достаточно средств
            if amount > user.balance:
                return JsonResponse({'success': False, 'errors': {'amount': ['Недостаточно средств.']}}, status=400)

            # Обновляем баланс пользователя, списывая сумму
            user.balance -= amount
            user.save()

            # Сохраняем запрос на вывод
            withdrawal = form.save(commit=False)
            withdrawal.user = user  # Устанавливаем пользователя
            withdrawal.save()

            return JsonResponse({'success': True, 'message': 'Запрос на вывод успешно создан.'}, status=201)
        else:
            # Если есть ошибки валидации, возвращаем их
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)



@method_decorator(csrf_exempt, name='dispatch')  # Для защиты CSRF можно убрать в будущем, если запросы из тех же источников
@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class CardsCreateView(CreateView):
    model = Cards
    form_class = CardsForm
    success_url = reverse_lazy('useraccount:withdraw')

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.instance.user = self.request.user
            form.save()
            return JsonResponse({'success': True, 'message': 'Карта успешно добавлена'}, status=201)
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required(login_url='useraccount:login'), name='dispatch')
class CardsUpdateView(UpdateView):
    model = Cards
    form_class = CardsForm
    success_url = reverse_lazy('useraccount:withdraw')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            form.instance.user = self.request.user
            form.save()
            return JsonResponse({'success': True, 'message': 'Карта успешно обновлена'}, status=200)
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
