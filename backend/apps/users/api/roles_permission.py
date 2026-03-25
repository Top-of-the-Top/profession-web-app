from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied
from apps.courses.models import Course

def require_role(*allowed_roles):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                return Response(
                    {'detail': 'Требуется аутентификация'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            user_role = getattr(request.user, 'role', None)

            if user_role not in allowed_roles:
                return Response(
                    {'detail': f'Доступ запрещен. Требуется роль: {", ".join(allowed_roles)}'},
                    status=status.HTTP_403_FORBIDDEN
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


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


def require_object_owner(model_class, lookup_field='pk'):

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                return Response(
                    {'detail': 'Требуется аутентификация'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if request.user.is_moderator():
                return view_func(request, *args, **kwargs)

            object_id = kwargs.get(lookup_field)
            if not object_id:
                return Response(
                    {'detail': f'Не указан параметр {lookup_field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                obj = model_class.objects.get(pk=object_id)

                owner = None
                if hasattr(obj, 'user'):
                    owner = obj.user
                elif hasattr(obj, 'author'):
                    owner = obj.author
                elif hasattr(obj, 'created_by'):
                    owner = obj.created_by

                if owner and owner != request.user:
                    return Response(
                        {'detail': 'Доступ запрещен. Вы не являетесь владельцем этого объекта'},
                        status=status.HTTP_403_FORBIDDEN
                    )

            except model_class.DoesNotExist:
                return Response(
                    {'detail': 'Объект не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class RolePermissionMixin:
    required_roles = None

    def check_role_permission(self):
        if not self.request.user or not self.request.user.is_authenticated:
            raise PermissionDenied('Требуется аутентификация')

        if self.required_roles:
            user_role = getattr(self.request.user, 'role', None)
            if user_role not in self.required_roles:
                raise PermissionDenied(
                    f'Доступ запрещен. Требуется роль: {", ".join(self.required_roles)}'
                )

    def dispatch(self, request, *args, **kwargs):
        """Переопределяем dispatch для проверки ролей"""
        self.check_role_permission()
        return super().dispatch(request, *args, **kwargs)
