from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/blogs/(?P<blog_id>\d+)/chat/$', consumers.BlogChatConsumer.as_asgi()),
    re_path(r'^ws/audio/(?P<user_id>\d+)/$', consumers.AudioConsumer.as_asgi()),

]
