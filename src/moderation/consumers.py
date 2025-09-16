import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.db import database_sync_to_async
from .models import CallSession

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



class AudioConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope.get("user")
        self.user_id_from_url = self.scope['url_route']['kwargs'].get('user_id')
        print("Audio WS: connect", self.user, self.user_id_from_url)

        # проверим авторизацию
        if not self.user or not self.user.is_authenticated:
            self.close()
            return

        # если хочешь, можешь сверить id из URL и id авторизованного пользователя:
        if str(self.user.id) != str(self.user_id_from_url):
            self.close()
            return

        self.accept()
        self.send(text_data=json.dumps({"type": "ready", "user_id": self.user_id_from_url}))

