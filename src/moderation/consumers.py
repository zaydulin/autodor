import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.db import database_sync_to_async
from .models import CallSession
from django.conf import settings
import os, uuid, json, time
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

        os.makedirs(AUDIO_DIR, exist_ok=True)
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
            self.fh = open(self.file_path, "ab")
            self.start_time = time.time()
            self.saved = False
            print(f"Audio WS: new file started -> {self.filename}")
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
            rel_path = os.path.join("audio", self.filename)

            try:
                record = Record.objects.create(user=self.user)
                record.audio.name = rel_path
                record.save(update_fields=["audio"])
                print(f"Audio WS: Record saved -> {rel_path}")
                self.saved = True
            except Exception as e:
                print(f"Failed to save record: {e}")
