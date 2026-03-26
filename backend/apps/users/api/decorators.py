from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied
from apps.courses.models import Course

# TODO: Семен у меня это упало при /app/courses, отдал нейронке логи, она точечно только тут поправила. Откати назад если не то что то

#
# Исправил падение `500` на `/api/app/courses/`: проблема была в декораторах доступа для DRF `ViewSet`.

# - В `backend/apps/users/api/decorators.py` декораторы ожидали сигнатуру `wrapper(request, ...)`, но для методов `ViewSet` первым аргументом приходит `self`.
# - Из-за этого `request` фактически был объектом `CourseViewSet`, и происходил `AttributeError: 'CourseViewSet' object has no attribute 'user'`.
# - Я переделал `require_moderator`, `require_course_author`, `require_course_enrollment` на универсальную сигнатуру `wrapper(*args, **kwargs)` и добавил извлечение `request` через helper `_extract_request(args)`.
# - Вызов оборачиваемой функции теперь идёт как `view_func(*args, **kwargs)`, чтобы корректно работало и для методов класса, и для function-based view.
# - Добавил защиту на случай, если `request` не удалось определить (возвращается `400` вместо крэша).
# 





def _extract_request(args):
    if not args:
        return None

    first_arg = args[0]
    if hasattr(first_arg, "user"):
        return first_arg

    if len(args) > 1 and hasattr(args[1], "user"):
        return args[1]

    return None

def require_moderator(view_func):

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        request = _extract_request(args)
        if request is None:
            return Response(
                {'detail': 'Не удалось определить запрос'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется аутентификация'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not request.user.is_moderator():
            return Response(
                {'detail': 'Доступ запрещен. Требуется роль модератора'},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(*args, **kwargs)
    return wrapper


def require_course_author(view_func):

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        request = _extract_request(args)
        if request is None:
            return Response(
                {'detail': 'Не удалось определить запрос'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется аутентификация'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if request.user.is_moderator(): # им можно все
            return view_func(*args, **kwargs)

        if not request.user.is_teacher(): # сразу кик студентов
            return Response(
                {'detail': 'Доступ запрещен. Требуется роль преподавателя'},
                status=status.HTTP_403_FORBIDDEN
            )

        course_id = kwargs.get('course_id') or kwargs.get('pk')
        if not course_id and args:
            course_id = args[0] if len(args) > 0 else None

        if not course_id:
            return Response(
                {'detail': 'Не указан ID курса'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = Course.objects.get(id=course_id)
            if not request.user.is_course_author(course):
                return Response(
                    {'detail': 'Доступ запрещен. Требуется роль автора курса'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Course.DoesNotExist:
            return Response(
                {'detail': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        return view_func(*args, **kwargs)
    return wrapper

def require_course_enrollment(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        request = _extract_request(args)
        if request is None:
            return Response(
                {'detail': 'Не удалось определить запрос'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется аутентификация'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if request.user.is_moderator():
            return view_func(*args, **kwargs)

        course_slug = (
            kwargs.get('course_slug') or # TODO: оптимизировать данную штуку, рефакторить поле класса на course_slug для всех моделей для удобства
            kwargs.get('slug')
        )

        if not course_slug:
            return Response(
                {'detail': 'Не указан slug курса'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = Course.objects.get(slug=course_slug)

            if request.user.is_teacher() and request.user.is_course_author(course):
                return view_func(*args, **kwargs)

            if not request.user.is_enrolled(course):
                return Response(
                    {'detail': 'Вы не записаны на этот курс'},
                    status=status.HTTP_403_FORBIDDEN
                )

        except Course.DoesNotExist:
            return Response(
                {'detail': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        return view_func(*args, **kwargs)
    return wrapper
