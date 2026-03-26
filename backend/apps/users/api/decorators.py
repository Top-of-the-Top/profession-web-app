from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied
from apps.courses.models import Course

def require_moderator(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
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

        return view_func(request, *args, **kwargs)
    return wrapper


def require_course_author(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется аутентификация'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if request.user.is_moderator(): # им можно все
            return view_func(request, *args, **kwargs)

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

        return view_func(request, *args, **kwargs)
    return wrapper

def require_course_enrollment(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется аутентификация'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if request.user.is_moderator():
            return view_func(request, *args, **kwargs)

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
                return view_func(request, *args, **kwargs)

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

        return view_func(request, *args, **kwargs)
    return wrapper
