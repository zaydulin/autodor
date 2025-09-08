from django.conf import settings
from firebase_admin import messaging, exceptions
from useraccount.models import Profile

def send_firebase_notification(user_id, title, message, image_url=None):
    """
    Отправляет push-уведомление через Firebase для указанного пользователя.
    """
    try:
        # Получаем пользователя
        user = Profile.objects.get(id=user_id)
        if not user.device_token:
            print(f"Пользователь {user_id} не имеет токена устройства.")
            return {"success": False, "message": "Пользователь не имеет токена устройства"}

        print(f"Отправка уведомления пользователю {user_id} с токеном: {user.device_token}")

        # Обычное уведомление (для фонового режима и заблокированного экрана)
        notification = messaging.Notification(
            title=title,
            body=message,
            image=image_url
        )

        # Data-поле (позволяет обработать уведомление в Foreground)
        data_payload = {
            "title": title,
            "body": message,
            "image_url": image_url if image_url else "",
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "sound_url": f"{settings.MEDIA_URL}notification.wav"  # Только для обработки вручную
        }

        # Конфигурация для Android (уведомление + звук)
        android_config = messaging.AndroidConfig(
            notification=messaging.AndroidNotification(
                sound="default",
                click_action="FLUTTER_NOTIFICATION_CLICK"
            ),
            priority="high"
        )

        # Конфигурация для iOS
        apns_config = messaging.APNSConfig(
            headers={"apns-priority": "10"},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound="default",
                    content_available=True  # Позволяет получать уведомления в фоне
                )
            )
        )

        # Создаем сообщение
        message = messaging.Message(
            notification=notification,  # Обычное уведомление (для фонового режима)
            data=data_payload,  # Data-уведомление (для Foreground)
            token=user.device_token,
            android=android_config,
            apns=apns_config
        )

        # Отправляем уведомление
        response = messaging.send(message)
        print(f"Уведомление успешно отправлено. Ответ: {response}")
        return {"success": True, "response": response}

    except Profile.DoesNotExist:
        print(f"Пользователь {user_id} не найден.")
        return {"success": False, "message": "Пользователь не найден"}
    except exceptions.FirebaseError as e:
        print(f"Ошибка Firebase: {e}")
        return {"success": False, "message": f"Ошибка Firebase: {e}"}
    except Exception as e:
        print(f"Другая ошибка: {e}")
        return {"success": False, "message": str(e)}
