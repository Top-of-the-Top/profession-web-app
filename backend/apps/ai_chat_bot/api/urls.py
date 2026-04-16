from django.urls import path
from .views import AIChatWebSocketSchemaView

app_name = 'ai_chat_bot'


urlpatterns = [
    path('app/courses/<slug:course_slug>/ai/chat/docs/', AIChatWebSocketSchemaView.as_view(), name='ai_chat_ws_docs'),
]