from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from webmain.models import MessagesChat, Blogs
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Record, Profile
import os, uuid, json
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
        try:
            self.user = self.scope.get("user")
            self.position_from_url = self.scope["url_route"]["kwargs"].get("position")

            print("Audio WS: connect", self.user, "pos_from_url:", self.position_from_url)

            # Проверяем, авторизован ли пользователь
            if not getattr(self.user, "is_authenticated", False):
                print("Anonymous user -> close")
                self.close()
                return

            # Сверяем position
            user_position = getattr(self.user, "position", None)
            if str(user_position) != str(self.position_from_url):
                print("Position mismatch:", user_position, self.position_from_url)
                self.close()
                return

            self.accept()
            self.send(text_data=json.dumps({
                "type": "ready",
                "position": self.position_from_url
            }))

        except Exception:
            import traceback; traceback.print_exc()
            self.close()



