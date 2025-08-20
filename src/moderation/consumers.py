import json

from channels.generic.websocket import AsyncWebsocketConsumer


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.user = self.scope['user']
        self.user_id = self.user.id
        self.group_name = f'user_{self.user_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'call_incoming':
            # Отправляем вызываемому пользователю
            target_user_id = data.get('target_user_id')
            await self.channel_layer.group_send(
                f'user_{target_user_id}',
                {
                    'type': 'incoming_call',
                    'call_id': data.get('call_id'),
                    'caller_id': self.user_id,
                }
            )
        elif message_type == 'hangup':
            # Рассылаем всем участникам
            await self.channel_layer.group_send(
                f'call_{self.call_id}',
                {
                    'type': 'call_hangup',
                    'sender': self.user_id,
                }
            )
        else:
            # Передача WebRTC сигналов
            target_user_id = data.get('target_user_id')
            if target_user_id:
                await self.channel_layer.group_send(
                    f'user_{target_user_id}',
                    {
                        'type': 'send_message',
                        'message': data,
                    }
                )

    async def incoming_call(self, event):
        await self.send(text_data=json.dumps({
            'type': 'incoming_call',
            'call_id': event['call_id'],
            'caller_id': event['caller_id'],
        }))

    async def call_hangup(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_hangup',
            'sender': event['sender'],
        }))

    async def send_message(self, event):
        await self.send(text_data=json.dumps(event['message']))
