import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from webmain.models import MessagesChat, Blogs
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Record, Profile
import os
import uuid
from django.conf import settings

User = get_user_model()

class BlogChatConsumer(WebsocketConsumer):
    def connect(self):
        print("WebSocket CONNECT")
        self.blog_id = self.scope['url_route']['kwargs']['blog_id']
        self.blog = Blogs.objects.get(id=self.blog_id)
        self.room_group_name = f'blog_chat_{self.blog_id}'

        user = self.scope['user']
        if not user.is_authenticated:
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()

        # Отправляем все существующие сообщения
        messages = MessagesChat.objects.filter(ticket=self.blog).order_by("date")
        for message in messages:
            self.send(text_data=json.dumps({
                'message_id': message.id,
                'content': message.content,
                'author': message.author.username,
                'author_id': message.author.id,
                'date': timezone.localtime(message.date).strftime("%H:%M"),
                'blog_id': self.blog_id
            }))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('content')
        author_id = data.get('author_id')

        try:
            author = User.objects.get(id=author_id)
            message = MessagesChat.objects.create(
                content=content,
                author=author,
                ticket=self.blog
            )

            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message.id,
                    'content': content,
                    'author': author.username,
                    'author_id': author.id,
                    'date': timezone.localtime(message.date).strftime("%H:%M"),
                    'blog_id': self.blog_id
                }
            )
        except Exception as e:
            self.send(text_data=json.dumps({'error': str(e)}))

    def chat_message(self, event):
        self.send(text_data=json.dumps(event))

AUDIO_DIR = os.path.join(settings.MEDIA_ROOT, "audio")

class AudioConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope.get("user")
        self.username_from_url = self.scope['url_route']['kwargs'].get('username')

        print("Audio WS: connect", self.user, self.username_from_url)

        if not self.user or not self.user.is_authenticated:
            self.close()
            return

        # Проверяем, что подключается именно сам пользователь
        if self.user.username != self.username_from_url:
            self.close()
            return

        self.file_path = None
        self.fh = None
        self.filename = None
        self.saved = False

        if not os.path.exists(AUDIO_DIR):
            os.makedirs(AUDIO_DIR, exist_ok=True)

        self.accept()
        self.send(text_data=json.dumps({"type": "ready", "username": self.username_from_url}))

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
                self.send(text_data=json.dumps({"type": "started", "filename": self.filename}))
                return

            if action == "stop":
                self._finalize_record()
                self.send(text_data=json.dumps({"type": "stopped", "filename": self.filename}))
                self.close()
                return

        if bytes_data:
            if self.fh is None:
                self.filename = f"{uuid.uuid4()}.webm"
                self.file_path = os.path.join(AUDIO_DIR, self.filename)
                self.fh = open(self.file_path, "ab")
            self.fh.write(bytes_data)

    def disconnect(self, close_code):
        print(f"Audio WS: disconnect {close_code}")
        self._finalize_record()

    def _finalize_record(self):
        if self.fh and not self.fh.closed:
            self.fh.close()

        if self.file_path and os.path.exists(self.file_path) and not self.saved:
            rel_path = os.path.join("audio", self.filename)
            record = Record.objects.create(user=self.user)
            record.audio.name = rel_path
            record.save(update_fields=["audio"])
            self.saved = True

