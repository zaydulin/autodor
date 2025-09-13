import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_project.settings')

import django
django.setup() 

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import moderation.routing

django_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_app(),
    "websocket": AuthMiddlewareStack (
        URLRouter(
            moderation.routing.websocket_urlpatterns
        ),
    )
})
