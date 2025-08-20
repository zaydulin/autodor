import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from .models import CallSession
from asgiref.sync import sync_to_async

class CallConsumer(WebsocketConsumer):
    def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.room_group_name = f'call_{self.call_id}'

        return self.channel_layer.group_add(self.room_group_name, self.channel_name)
        return self.accept()

    def disconnect(self, close_code):
        return self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'hangup':
            # Обработка завершения звонка
            return self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': '',
                    'message': {
                        'type': 'hangup',
                        'sender': data.get('sender'),
                    }
                }
            )
        else:
            # Обработка других сигналов
            return self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_message',
                    'message': data,
                }
            )

    def send_message(self, event):
        # Унифицированный метод отправки сообщений
        return self.send(text_data=json.dumps(event['message']))
