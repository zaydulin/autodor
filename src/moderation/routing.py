from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/call/(?P<call_id>\d+)/$", consumers.CallConsumer.as_asgi()),
    re_path(r"^ws/audio/(?P<position>\d+)/?$", consumers.AudioConsumer.as_asgi()),

]
