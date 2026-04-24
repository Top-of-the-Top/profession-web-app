from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware


@database_sync_to_async
def _resolve_user(token):
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.authentication import JWTAuthentication

    if not token:
        return AnonymousUser()
    try:
        authenticator = JWTAuthentication()
        validated = authenticator.get_validated_token(token)
        return authenticator.get_user(validated)
    except Exception:
        return AnonymousUser()


class WebSocketJWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = None

        for header, value in scope.get("headers", []):
            if header == b"authorization":
                raw = value.decode("utf-8", errors="ignore")
                if raw.lower().startswith("bearer "):
                    token = raw.split(" ", 1)[1].strip()
                break

        if not token:
            query_string = scope.get("query_string", b"").decode("utf-8")
            token = parse_qs(query_string).get("token", [None])[0]

        scope["user"] = await _resolve_user(token)
        return await super().__call__(scope, receive, send)
