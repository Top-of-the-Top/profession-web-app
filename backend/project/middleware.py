import logging
import sys
import time
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

logger = logging.getLogger(__name__)


class Term:
    GRAY = "\033[90m"
    CYAN = "\033[36m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start

        status = response.status_code
        if status < 400:
            status_color = Term.GREEN
        elif status < 500:
            status_color = Term.YELLOW
        else:
            status_color = Term.RED

        time_color = Term.MAGENTA
        if duration > 0.5:
            time_color = Term.RED + Term.BOLD

        log_entry = (
            f"{Term.GRAY}{Term.RESET}{Term.YELLOW}SYNC{Term.RESET}{Term.GRAY}{Term.RESET} "
            f"{Term.GRAY}|{Term.RESET} {Term.WHITE}{Term.BOLD}{request.method:<7}{Term.RESET} "
            f"{Term.GRAY}|{Term.RESET} {Term.CYAN}{request.path:<40}{Term.RESET} "
            f"{Term.GRAY}|{Term.RESET} {status_color}{status:<3}{Term.RESET} "
            f"{Term.GRAY}|{Term.RESET} {time_color}{duration:.4f}s{Term.RESET}"
        )

        sys.stdout.write(log_entry + "\n")
        sys.stdout.flush()

        return response


@database_sync_to_async
def _resolve_user(token):
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.authentication import JWTAuthentication

    if not token:
        logger.warning("WS auth failed: token is missing")
        return AnonymousUser()
    try:
        authenticator = JWTAuthentication()
        validated = authenticator.get_validated_token(token)
        logger.info("WS auth token validated for user_id=%s", validated.get("user_id"))
        return authenticator.get_user(validated)
    except Exception as exc:
        logger.warning("WS auth failed: %s", exc)
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
