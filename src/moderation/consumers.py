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

