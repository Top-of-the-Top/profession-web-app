from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def _extract_request(args):
    if not args:
        return None
    return args[0] if hasattr(args[0], 'user') else (args[1] if len(args) > 1 else None)


def require_moderator(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        request = _extract_request(args)
        if request is None or not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется авторизация'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not request.user.is_moderator():
            return Response(
                {'detail': 'Доступ запрещен. Требуется роль модератора'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return view_func(*args, **kwargs)
    return wrapper
