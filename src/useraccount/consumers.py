import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from webmain.models import MessagesChat, Blogs
from django.contrib.auth import get_user_model
from django.utils import timezone

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
