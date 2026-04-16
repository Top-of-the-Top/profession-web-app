from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'^api/app/course/(?P<course_slug>[-a-zA-Z0-9_]+)/ai/chat/$', 
        consumers.ChatConsumer.as_asgi()
    ),
]