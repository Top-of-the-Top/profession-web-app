from django.http import JsonResponse
from django.views import View


class AIChatWebSocketSchemaView(View):
    def get(self, request, course_slug, *args, **kwargs):
        return JsonResponse(
            {
                "name": "AI Chat WebSocket",
                "path": f"/api/app/course/{course_slug}/ai/chat/",
                "auth": "JWT access token in query param `token` or `Authorization: Bearer <token>` header",
                "request_example": {"message": "Привет, помоги с уроком"},
                "response_types": [
                    {"type": "chunk", "content": "partial answer"},
                    {"type": "error", "content": "error message"},
                ],
            }
        )
