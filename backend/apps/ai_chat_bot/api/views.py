from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

class AIChatWebSocketSchemaView(APIView):

    @extend_schema(
        summary="[WebSocket] ИИ-чат ассистент",
        description=(
            "### Описание протокола\n"
            "Этот эндпоинт работает по протоколу **WebSocket**.\n\n"
            "**URL для подключения:** `ws://domain/api/app/course/{course_slug}/ai/chat/`\n\n"
            "**Авторизация:** Токен передается в query-параметре: `?token=YOUR_JWT_TOKEN`"
            "**Логика:** После установки соединения отправьте JSON с вопросом. Ответ придет в виде потока чанков."
        ),
        request=inline_serializer(
            name='WebSocketChatInput',
            fields={
                'message': serializers.CharField(help_text="Текст сообщения пользователя")
            }
        ),
        responses={
            200: inline_serializer(
                name='WebSocketChatResponse',
                fields={
                    'type': serializers.ChoiceField(choices=['chunk', 'error', 'done']),
                    'content': serializers.CharField(help_text="Содержимое (текст ответа или ошибка)")
                }
            )
        },
        tags=['AI Chat']
    )
    def get(self, request, *args, **kwargs):
        return Response(
            {"detail": "Используйте протокол WebSocket для этого адреса."},
            status=status.HTTP_426_UPGRADE_REQUIRED
        )