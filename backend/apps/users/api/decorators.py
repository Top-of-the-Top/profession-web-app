from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from apps.courses.models import Course


def _extract_request(args):
    if not args:
        return None
    if (hasattr(args[0], 'user')):
        request = args[0]
    else :
        request = args[1]

    return request


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

        if request.user.is_moderator():
            return view_func(*args, **kwargs)

        if not request.user.is_teacher():
            return Response(
                {'detail': 'Доступ запрещен. Требуется роль преподавателя'},
                status=status.HTTP_403_FORBIDDEN
            )

        course_slug = kwargs.get('course_slug') or kwargs.get('slug') or kwargs.get('pk')

        if not course_slug:
            course_id = kwargs.get('course_id')
            if course_id:
                try:
                    course = Course.objects.get(course_id=course_id)
                except Course.DoesNotExist:
                    return Response(
                        {'detail': 'Курс не найден'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                return Response(
                    {'detail': 'Не указан ID или slug курса'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            try:
                course = Course.objects.get(slug=course_slug)
            except Course.DoesNotExist:
                return Response(
                    {'detail': 'Курс не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

        if not request.user.is_course_author(course):
            return Response(
                {'detail': 'Доступ запрещен. Требуется роль автора курса'},
                status=status.HTTP_403_FORBIDDEN
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

        course_slug = kwargs.get('course_slug') or kwargs.get('slug')

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
