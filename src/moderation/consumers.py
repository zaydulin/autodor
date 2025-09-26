# moderation/consumers.py
import json
import os
import uuid
import time
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from django.core.files import File
from channels.db import database_sync_to_async
from django.conf import settings
from useraccount.models import Record, Profile
from moderation.models import AdvertAplication, ChatMessage, CallSession

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
        self.application_id = self.scope['url_route']['kwargs']['application_id']
        self.room_group_name = f'chat_{self.application_id}'

        # Проверка доступа к приложению
        if await self.has_access():
            # Присоединяемся к группе
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

            # Отправляем историю сообщений
            await self.send_history()

            # Уведомляем о подключении
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'user_id': self.scope['user'].id,
                    'user_name': f"{self.scope['user'].first_name} {self.scope['user'].last_name}"
                }
            )
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Уведомляем о выходе
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user_id': self.scope['user'].id,
                    'user_name': f"{self.scope['user'].first_name} {self.scope['user'].last_name}"
                }
            )

            # Покидаем группу
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'chat_message':
            await self.handle_chat_message(data)
        elif message_type == 'user_joined':
            await self.handle_user_joined(data)
        elif message_type == 'user_left':
            await self.handle_user_left(data)

    async def handle_chat_message(self, data):
        # Сохраняем сообщение в БД
        message = await self.save_message(
            data['message'],
            data['user_id'],
            self.application_id
        )

        # Отправляем сообщение в группу
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'author_id': message.author.id,
                    'author_name': f"{message.author.first_name} {message.author.last_name}",
                    'timestamp': message.timestamp.isoformat()
                }
            }
        )

    async def handle_user_joined(self, data):
        # Уведомляем группу о подключении пользователя
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': data['user_id'],
                'user_name': data['user_name']
            }
        )

    async def handle_user_left(self, data):
        # Уведомляем группу о выходе пользователя
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': data['user_id'],
                'user_name': data['user_name']
            }
        )

    async def chat_message(self, event):
        # Отправляем сообщение WebSocket клиенту
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event['user_id'],
            'user_name': event['user_name']
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id'],
            'user_name': event['user_name']
        }))

    async def send_history(self):
        # Отправляем последние 50 сообщений
        messages = await self.get_message_history()
        await self.send(text_data=json.dumps({
            'type': 'message_history',
            'messages': messages
        }))

    @database_sync_to_async
    def has_access(self):
        """Проверка доступа пользователя к приложению"""
        try:
            application = AdvertAplication.objects.get(id=self.application_id)
            user = self.scope['user']

            # Проверяем, является ли пользователь участником приложения
            return (user in application.user.all() or
                    user in application.user_menager.all() or
                    user in application.user_drivers.all())
        except AdvertAplication.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, user_id, application_id):
        """Сохранение сообщения в БД"""
        user = Profile.objects.get(id=user_id)
        application = AdvertAplication.objects.get(id=application_id)

        message = ChatMessage.objects.create(
            content=content,
            author=user,
            application=application
        )
        return message

    @database_sync_to_async
    def get_message_history(self):
        """Получение истории сообщений"""
        messages = ChatMessage.objects.filter(
            application_id=self.application_id
        ).select_related('author').order_by('-timestamp')[:50]

        return [
            {
                'id': msg.id,
                'content': msg.content,
                'author_id': msg.author.id,
                'author_name': f"{msg.author.first_name} {msg.author.last_name}",
                'timestamp': msg.timestamp.isoformat()
            }
            for msg in messages
        ]


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