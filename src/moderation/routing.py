from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/call/(?P<call_id>\d+)/$", consumers.CallConsumer.as_asgi()),
    re_path(r"ws/notify/(?P<user_id>[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/$", consumers.NotifyConsumer.as_asgi()),

    # re_path(r'ws/tracking/(?<aplications_id>[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/$', consumers.DriverTrackingConsumer.as_asgi()),

    re_path(
        r'^ws/chat/(?P<applications_id>[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/$',
        consumers.ChatConsumer.as_asgi()
    ),
    re_path(
        r'^ws/audio/(?P<user_id>[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/$',
        consumers.AudioConsumer.as_asgi()
    ),

]
