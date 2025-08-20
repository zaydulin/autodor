import json
from channels.generic.websocket import WebsocketConsumer
from .models import CallSession

class CallConsumer(WebsocketConsumer):
    def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.room_group_name = f'call_{self.call_id}'

        # Присоединяемся к группе
        self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        # Покидаем группу
        self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'hangup':
            # Обработка завершения звонка
            self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_hangup',  # вызывается метод send_call_hangup
                    'message': {
                        'type': 'hangup',
                        'sender': data.get('sender'),
                    }
                }
            )
        else:
            # Обработка других сигналов
            self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_message',  # вызывается метод send_message
                    'message': data,
                }
            )

    def send_message(self, event):
        # Отправляем сообщение клиенту
        self.send(text_data=json.dumps(event['message']))

    def call_hangup(self, event):
        # Обработка события hangup
        self.send(text_data=json.dumps(event['message']))
