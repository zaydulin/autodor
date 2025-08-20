import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import CallSession
from asgiref.sync import sync_to_async

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.room_group_name = f'call_{self.call_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def call_ended(self, event):
        # Отправляем всем участникам сообщение о завершении
        print(event)
        await self.send(text_data=json.dumps({
            'type': 'call_ended',
            'sender': event.get('sender'),
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'call_incoming':
            # Пользователю приходит уведомление о входящем звонке
            call_id = data.get('call_id')
            caller_id = data.get('caller_id')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'incoming_call',
                    'call_id': call_id,
                    'caller_id': caller_id,
                }
            )
        elif message_type == 'hangup':
            # Обработка завершения звонка
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_hangup',
                    'sender': data.get('sender'),
                }
            )
        else:
            # Передача сигналов WebRTC
            target_user_id = data.get('target_user_id')
            if target_user_id:
                await self.channel_layer.group_send(
                    f'user_{target_user_id}',
                    {
                        'type': 'send_message',
                        'message': data,
                    }
                )

    async def send_message(self, event):
        # Унифицированный метод отправки сообщений
        await self.send(text_data=json.dumps(event['message']))

    async def call_hangup(self, event):
        # Обработка события hangup
        await self.send(text_data=json.dumps({
            'type': 'call_hangup',
            'sender': event.get('sender'),
        }))
