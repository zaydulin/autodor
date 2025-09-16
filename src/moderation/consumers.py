import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.db import database_sync_to_async
from .models import CallSession
from django.conf import settings
import os, uuid, json
from useraccount.models import Record

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


AUDIO_DIR = os.path.join(settings.MEDIA_ROOT, "audio")

class AudioConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope.get("user")
        self.user_id_from_url = self.scope['url_route']['kwargs'].get("user_id")
        print("Audio WS: connect", self.user, self.user_id_from_url)

        # проверим авторизацию
        if not self.user or not self.user.is_authenticated:
            self.close()
            return

        # сверим id пользователя
        if str(self.user.id) != str(self.user_id_from_url):
            print("Audio WS: mismatch user_id")
            self.close()
            return

        os.makedirs(AUDIO_DIR, exist_ok=True)
        self.fh = None
        self.filename = None
        self.saved = False

        self.accept()
        self.send(text_data=json.dumps({"type": "ready", "user_id": self.user_id_from_url}))

    def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
            except Exception:
                data = {}

            action = data.get("action")

            if action == "start" and self.fh is None:
                ext = "webm" if data.get("mime") == "audio/webm" else "ogg"
                self.filename = f"{uuid.uuid4()}.{ext}"
                self.file_path = os.path.join(AUDIO_DIR, self.filename)
                self.fh = open(self.file_path, "ab")
                print("Audio WS: started ->", self.filename)
                self.send(text_data=json.dumps({"type": "started", "filename": self.filename}))
                return

            if action == "stop":
                self._finalize_record()
                self.send(text_data=json.dumps({"type": "stopped", "filename": self.filename}))
                self.close()
                return

        if bytes_data:
            if self.fh is None:
                # на всякий случай создаём файл, если пришли байты до "start"
                self.filename = f"{uuid.uuid4()}.webm"
                self.file_path = os.path.join(AUDIO_DIR, self.filename)
                self.fh = open(self.file_path, "ab")
            self.fh.write(bytes_data)

    def disconnect(self, close_code):
        print("Audio WS: disconnect", close_code)
        self._finalize_record()

    def _finalize_record(self):
        if getattr(self, "fh", None) and not self.fh.closed:
            self.fh.close()

        if getattr(self, "file_path", None) and os.path.exists(self.file_path) and not getattr(self, "saved", False):
            rel_path = os.path.join("audio", self.filename)

            record = Record.objects.create(user=self.user)
            record.audio.name = rel_path
            record.save(update_fields=["audio"])

            print("Audio WS: Record saved ->", rel_path)
            self.saved = True
