from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from useraccount.models import Notification, ApplicationsProduct, Profile
from .utils import send_firebase_notification
import threading
import time

@receiver(post_save, sender=Notification)
def send_notification_on_create(sender, instance, created, **kwargs):
    """
    Отправляет push-уведомление при создании нового уведомления с type=0.
    """
    if created and instance.type == 0:  # Проверяем, что type = 0
        print(f"Создано новое уведомление с type=0 для пользователя {instance.user.id}.")

        # Подготовка данных для отправки
        title = instance.title or "Новое уведомление"
        message = instance.message or "У вас новое уведомление"
        image_url = instance.image.url if instance.image else None

        # Отправляем уведомление
        response = send_firebase_notification(
            user_id=instance.user.id,
            title=title,
            message=message,
            image_url=image_url
        )

        # Выводим результат отправки
        if response.get("success"):
            print(f"Уведомление успешно отправлено пользователю {instance.user.id}. Ответ: {response['response']}")
        else:
            print(f"Ошибка отправки уведомления пользователю {instance.user.id}: {response['message']}")

@receiver(post_save, sender=ApplicationsProduct)
def create_or_update_notification(sender, instance, created, **kwargs):
    if created:
        title = f"Новая заявка создана: {instance.id}"
        message = f"Заявка с адресом доставки {instance.adress_b} была успешно создана."
    else:
        title = f"Заявка обновлена: {instance.id}"
        message = f"Заявка с адресом доставки {instance.adress_b} была обновлена."

    # Фильтруем только пользователей с типом "Партнёр" (type=3)
    partners = instance.users.filter(type=3)

    for user in partners:
        Notification.objects.create(
            type=0,
            status=1,
            user=user,
            title=title,
            message=message,
        )

@receiver(m2m_changed, sender=ApplicationsProduct.users.through)
def handle_users_changed(sender, instance, action, **kwargs):
    # Создаем уведомления при изменении ManyToManyField `users`
    if action in ['post_add', 'post_remove', 'post_clear']:
        title = f"Заявка обновлена: {instance.id}"
        message = f"Список пользователей для заявки с адресом {instance.adress_b} был обновлен."

        # Создаем уведомления для всех текущих пользователей
        users = instance.users.all()
        for user in users:
            Notification.objects.create(
                type=0,
                status=1,
                user=user,
                title=title,
                message=message,
            )


def notify_partners_until_accepted(app_id):
    print(f"[INFO] Запущен поток уведомлений для заявки {app_id}")
    while True:
        try:
            app = ApplicationsProduct.objects.get(id=app_id)

            if app.users.exists():
                print(f"[INFO] У заявки {app.id} появились пользователи. Останавливаем уведомления.")
                break  # Останавливаем цикл

            # Получаем всех пользователей с type=3 (Партнёры)
            partners = Profile.objects.filter(type=3, works=False)

            for partner in partners:
                Notification.objects.create(
                    type=0,
                    status=1,
                    user=partner,
                    title=f"Новая заявка: {app.id}",
                    message=f"Заявка по адресу {app.adress_b} ожидает принятия."
                )
                print(f"[INFO] Уведомление отправлено партнёру {partner.username}")

            time.sleep(5)

        except ApplicationsProduct.DoesNotExist:
            print(f"[WARNING] Заявка {app_id} удалена. Останавливаем поток.")
            break


@receiver(post_save, sender=ApplicationsProduct)
def start_partner_notifications(sender, instance, created, **kwargs):
    if created:
        print(f"[SIGNAL] Обнаружено создание заявки {instance.id}, запускаем уведомления...")
        thread = threading.Thread(
            target=notify_partners_until_accepted,
            args=(instance.id,),
            daemon=True
        )
        thread.start()