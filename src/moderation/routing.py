from django.urls import re_path
from . import consumers
from django.urls import path

websocket_urlpatterns = [
    path('ws/call/<uuid:call_id>/', consumers.CallConsumer.as_asgi()),
]
