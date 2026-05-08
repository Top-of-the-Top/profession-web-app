import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.db import close_old_connections

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django_asgi_app = get_asgi_application()
from project.middleware import WebSocketJWTAuthMiddleware
from project.routing import websocket_urlpatterns


class CloseDbConnectionsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        finally:
            if scope["type"] == "http":
                close_old_connections()


application = ProtocolTypeRouter(
    {
        "http": CloseDbConnectionsMiddleware(django_asgi_app),
        "websocket": WebSocketJWTAuthMiddleware(
            URLRouter(websocket_urlpatterns),
        ),
    }
)
