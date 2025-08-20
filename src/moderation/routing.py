from django.urls import re_path
from . import consumers
from django.urls import path

websocket_urlpatterns = [
    re_path(r"ws/call/(?P<call_id>[0-9a-f\-]+)/$", consumers.CallConsumer.as_asgi()),
]
