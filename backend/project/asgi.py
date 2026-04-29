import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django_asgi_app = get_asgi_application()
from project.middleware import WebSocketJWTAuthMiddleware
from project.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': WebSocketJWTAuthMiddleware(
        URLRouter(websocket_urlpatterns),
    ),
})