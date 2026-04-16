import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from project.ws_auth import WebSocketJWTAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

django_asgi_app = get_asgi_application()

import apps.ai_chat_bot.api.routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': WebSocketJWTAuthMiddleware(
        URLRouter(apps.ai_chat_bot.api.routing.websocket_urlpatterns),
    ),
})