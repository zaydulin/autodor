# moderation/consumers.py
import json
import os
import uuid
import time

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.core.files import File
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from useraccount.models import Record, Profile
from moderation.models import AdvertAplication, ChatMessage, CallSession

from moderation.models import DriverLocation

AUDIO_DIR = os.path.join(settings.MEDIA_ROOT, "audio")


class AudioConsumer(WebsocketConsumer):
    MAX_DURATION = 15 * 60  # 15 минут в секундах

    def connect(self):
        self.user = self.scope.get("user")
        self.user_id_from_url = self.scope['url_route']['kwargs'].get("user_id")
        print("Audio WS: connect", self.user, self.user_id_from_url)

        # Проверка аутентификации и совпадения идентификаторов
        if not self.user or not self.user.is_authenticated:
            print("Audio WS: Unauthorized user, closing connection")
            self.close()
            return

        if str(self.user.id) != str(self.user_id_from_url):
            print("Audio WS: User ID mismatch, closing connection")
            self.close()
            return

        # Проверяем и создаём директорию, если её нет
        if not os.path.exists(AUDIO_DIR):
            print(f"Audio directory does not exist. Creating: {AUDIO_DIR}")
            try:
                os.makedirs(AUDIO_DIR, exist_ok=True)
                print(f"Created directory: {AUDIO_DIR}")
            except Exception as e:
                print(f"Failed to create audio directory: {e}")
                self.close()
                return

        self.fh = None
        self.filename = None
        self.start_time = None
        self.saved = False

        # Принимаем подключение WebSocket
        self.accept()
        self.send(text_data=json.dumps({"type": "ready"}))

    def _open_new_file(self, ext="webm"):
        """Создать новый файл и открыть дескриптор"""
        if self.fh and not self.fh.closed:
            self._finalize_record()

        self.filename = f"{uuid.uuid4()}.{ext}"
        self.file_path = os.path.join(AUDIO_DIR, self.filename)

        try:
            # Пытаемся создать файл
            self.fh = open(self.file_path, "ab")
            self.start_time = time.time()
            self.saved = False
            print(f"Audio WS: new file started -> {self.filename} at {self.file_path}")
        except Exception as e:
            print(f"Failed to open file {self.file_path}: {e}")
            self.close()

    def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
            except Exception:
                data = {}
            action = data.get("action")

            if action == "start":
                ext = "webm" if data.get("mime") == "audio/webm" else "ogg"
                self._open_new_file(ext)
                self.send(text_data=json.dumps({"type": "started", "filename": self.filename}))
                return

            if action == "stop":
                self._finalize_record()
                self.send(text_data=json.dumps({"type": "stopped", "filename": self.filename}))
                self.close()
                return

        if bytes_data:
            if self.fh is None:
                self._open_new_file("webm")

            # Проверка длительности
            if time.time() - self.start_time >= self.MAX_DURATION:
                print("Audio WS: 15 min reached, rotating file")
                self._open_new_file("webm")

            try:
                self.fh.write(bytes_data)
            except Exception as e:
                print(f"Failed to write data to file: {e}")

    def disconnect(self, close_code):
        print(f"Audio WS: disconnect {close_code}")
        self._finalize_record()

    def _finalize_record(self):
        """Закрыть файл и сохранить запись"""
        if getattr(self, "fh", None) and not self.fh.closed:
            self.fh.close()

        if getattr(self, "file_path", None) and os.path.exists(self.file_path) and not getattr(self, "saved", False):
            # Используйте относительный путь от MEDIA_ROOT
            rel_path = os.path.join("audio", self.filename)  # Путь относительно MEDIA_ROOT

            # Проверка на существование файла перед сохранением
            if not os.path.exists(self.file_path):
                print(f"File does not exist: {self.file_path}")
                return

            # Сохраняем файл с помощью Django FileField
            try:
                with open(self.file_path, 'rb') as f:
                    print(f"File exists and is being saved: {self.file_path}")
                    # Создаем объект Record и сохраняем файл в поле audio
                    record = Record.objects.create(user=self.user)
                    record.audio.save(self.filename, File(f), save=True)  # Используем относительный путь
                    print(f"Audio WS: Record saved -> {rel_path}")
                self.saved = True
            except Exception as e:
                print(f"Failed to save record: {e}")



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(">>> CONNECT: kwargs =", self.scope.get("url_route", {}).get("kwargs"))

        try:
            self.applications_id = self.scope['url_route']['kwargs']['applications_id']
            self.room_group_name = f"apllication_chat_{self.applications_id}"

            if not self.scope["user"].is_authenticated:
                print(">>> CONNECT: anonymous user -> close")
                await self.close(code=4001)
                return
            print(">>> CONNECT: user =", self.scope["user"].username)

            # загрузка
            self.applications = await self.get_application(self.applications_id)
            print(">>> CONNECT: AdvertApplication loaded id =", self.applications.id)

            messages = await self.get_messages(self.applications)
            print(f">>> CONNECT: messages loaded: {len(messages)}")

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            print(">>> CONNECT: accepted")

            # отправляем историю
            for m in messages:
                await self.send(text_data=json.dumps({
                    "type": "chat_message",
                    "message_id": str(m.id),  # <-- строка
                    "content": m.content,
                    "author": m.author.username if m.author else "",
                    "author_id": str(m.author.id) if m.author else None,  # <-- строка
                    "date": timezone.localtime(m.date).strftime("%H:%M"),
                    "applications_id": str(self.applications_id),  # <-- строка
                }))
            print(">>> CONNECT: history sent")

        except Exception as e:
            print("!!! CONNECT ERROR:", repr(e))
            await self.close(code=1000)  # <-- корректный код

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content")
        author_id = data.get("author_id")

        try:
            author = await self.get_author(author_id)
            msg = await self.create_message(content, author, self.applications)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message_id": str(msg.id),
                    "content": msg.content,
                    "author": author.username,
                    "author_id": str(author.id),  # <-- строка
                    "date": timezone.localtime(msg.date).strftime("%H:%M"),
                    "applications_id": str(self.applications_id),
                }
            )
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # --- обёртки для ORM ---
    @database_sync_to_async
    def get_application(self, app_id):
        return AdvertAplication.objects.get(id=app_id)

    @database_sync_to_async
    def get_messages(self, application):
        return list(ChatMessage.objects.filter(applications=application)
                    .select_related("author").order_by("date"))

    @database_sync_to_async
    def get_author(self, author_id):
        return Profile.objects.get(id=author_id)

    @database_sync_to_async
    def create_message(self, content, author, application):
        return ChatMessage.objects.create(content=content, author=author, applications=application)


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.room_group_name = f'call_{self.call_id}'

        # Проверяем существование сессии звонка
        if await self.call_session_exists():
            # Присоединяемся к группе
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Покидаем группу
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'hangup':
            # Обработка завершения звонка
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_hangup',
                    'message': {
                        'type': 'hangup',
                        'sender': data.get('sender'),
                    }
                }
            )
        else:
            # Обработка других сигналов
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_message',
                    'message': data,
                }
            )

    async def send_message(self, event):
        # Отправляем сообщение клиенту
        await self.send(text_data=json.dumps(event['message']))

    async def call_hangup(self, event):
        # Обработка события hangup
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def call_session_exists(self):
        return CallSession.objects.filter(id=self.call_id).exists()



class NotifyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f"user_notify_{self.user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        """Отправка произвольных уведомлений клиенту"""
        await self.send(text_data=json.dumps(event["payload"]))


class DriverTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.application_id = self.scope['url_route']['kwargs']['application_id']
        self.tracking_group_name = f'tracking_{self.application_id}'

        print(f"Tracking WS: Connecting to application {self.application_id}")

        # Проверяем доступ пользователя к отслеживанию
        if await self.has_tracking_access():
            await self.channel_layer.group_add(
                self.tracking_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"Tracking WS: Connected successfully")

            # Отправляем текущее местоположение при подключении
            current_location = await self.get_current_location()
            if current_location:
                await self.send_location_update(current_location)
            else:
                # Если нет текущего местоположения, отправляем пустые данные
                await self.send(text_data=json.dumps({
                    'type': 'no_location',
                    'message': 'Нет данных о местоположении'
                }))
        else:
            print("Tracking WS: Access denied")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'tracking_group_name'):
            await self.channel_layer.group_discard(
                self.tracking_group_name,
                self.channel_name
            )
        print(f"Tracking WS: Disconnected with code {close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            print(f"Tracking WS: Received action - {action}")

            if action == 'location_update' and self.scope["user"].employee == 3:  # только водители
                # Сохраняем местоположение от водителя
                location_data = await self.save_driver_location(data)
                if location_data:
                    # Рассылаем всем подписчикам
                    await self.channel_layer.group_send(
                        self.tracking_group_name,
                        {
                            'type': 'location_update',
                            'data': location_data
                        }
                    )

            elif action == 'get_location':
                # Запрос текущего местоположения
                current_location = await self.get_current_location()
                await self.send_location_update(current_location)

        except Exception as e:
            print(f"Tracking WS: Error processing message - {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def location_update(self, event):
        # Отправляем обновление местоположения клиенту
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'data': event['data']
        }))

    async def send_location_update(self, location_data):
        if location_data:
            await self.send(text_data=json.dumps({
                'type': 'location_update',
                'data': location_data
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'no_location',
                'message': 'Нет данных о местоположении'
            }))

    @database_sync_to_async
    def has_tracking_access(self):
        """Проверяет, имеет ли пользователь доступ к отслеживанию"""
        user = self.scope["user"]
        if isinstance(user, AnonymousUser):
            return False

        try:
            application = AdvertAplication.objects.get(id=self.application_id)

            # Проверяем, что заявка в статусе "в обработке"
            if application.status != 'in_progress':
                return False

            # Доступ имеют: водители этой заявки, менеджеры, администраторы
            has_access = (
                    user.employee in [2, 4] or  # менеджеры и админы
                    user in application.user_drivers.all() or  # водители заявки
                    user in application.user_menager.all()  # менеджеры заявки
            )

            print(f"Tracking access check - User: {user.id}, Employee: {user.employee}, Has access: {has_access}")
            return has_access

        except AdvertAplication.DoesNotExist:
            print(f"Application {self.application_id} not found")
            return False
        except Exception as e:
            print(f"Error checking tracking access: {e}")
            return False

    @database_sync_to_async
    def save_driver_location(self, data):
        """Сохраняет местоположение водителя"""
        try:
            application = AdvertAplication.objects.get(id=self.application_id)
            driver = self.scope["user"]

            # Проверяем, что пользователь действительно водитель этой заявки
            if driver not in application.user_drivers.all():
                print(f"Driver {driver.id} is not assigned to application {self.application_id}")
                return None

            # Создаем запись о местоположении
            location = DriverLocation.objects.create(
                application=application,
                driver=driver,
                latitude=data['latitude'],
                longitude=data['longitude'],
                accuracy=data.get('accuracy', 0),
                speed=data.get('speed', 0)
            )

            location_data = {
                'driver_id': str(driver.id),
                'driver_name': f"{driver.first_name} {driver.last_name}",
                'latitude': float(location.latitude),
                'longitude': float(location.longitude),
                'accuracy': location.accuracy,
                'speed': location.speed,
                'timestamp': location.timestamp.isoformat()
            }

            print(f"Location saved: {location_data}")
            return location_data

        except Exception as e:
            print(f"Error saving location: {e}")
            return None

    @database_sync_to_async
    def get_current_location(self):
        """Получает последнее известное местоположение водителя"""
        try:
            # Ищем последнее местоположение любого водителя этой заявки
            location = DriverLocation.objects.filter(
                application_id=self.application_id,
                is_active=True
            ).select_related('driver').latest('timestamp')

            return {
                'driver_id': str(location.driver.id),
                'driver_name': f"{location.driver.first_name} {location.driver.last_name}",
                'latitude': float(location.latitude),
                'longitude': float(location.longitude),
                'accuracy': location.accuracy,
                'speed': location.speed,
                'timestamp': location.timestamp.isoformat()
            }
        except DriverLocation.DoesNotExist:
            print(f"No location found for application {self.application_id}")
            return None