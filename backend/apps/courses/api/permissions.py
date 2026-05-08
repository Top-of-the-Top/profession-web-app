from functools import wraps

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from apps.core.api.permissions import _extract_request

from ..models import Course, Homework, Lesson, Section


def get_courses_for_user(user):
    if user.is_moderator():
        return Course.objects.all()
    purchased_ids = user.get_purchased_courses_ids()
    return Course.objects.filter(Q(authors=user) | Q(course_id__in=purchased_ids)).distinct()


class CourseContentVisibility:
    def __init__(self, user, course):
        self.user = user
        self.course = course
        self.is_moderator = user.is_moderator()
        self.is_author = user.is_course_author(course)
        self.see_drafts = self.is_moderator or self.is_author
        self.include_drafts = self.see_drafts
        self.cache_scope = "all" if self.see_drafts else "pub"
        self.show_types_in_tree = self.is_moderator or self.is_author

    def has_course_home_access(self):
        return self.user.is_enrolled(self.course) or self.is_author or self.is_moderator


def course_content_visibility(user, course):
    return CourseContentVisibility(user, course)


def published_lesson_hierarchy_q(lesson_field_prefix="lesson__"):
    return Q(
        **{
            f"{lesson_field_prefix}section__course__type": Course.PUBLISHED_STATUS,
            f"{lesson_field_prefix}section__type": Section.PUBLISHED_STATUS,
            f"{lesson_field_prefix}type": Lesson.PUBLISHED_STATUS,
        }
    )


def filter_homework_queryset_for_visibility(qs, include_drafts):
    if include_drafts:
        return qs
    return qs.filter(type=Homework.PUBLISHED_STATUS)


def _get_course_from_kwargs(kwargs):
    slug = kwargs.get("course_slug") or kwargs.get("slug") or kwargs.get("pk")
    if slug:
        try:
            return Course.objects.get(slug=slug), None
        except Course.DoesNotExist:
            return None, Response(
                {"detail": "Курс не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
    course_id = kwargs.get("course_id")
    if course_id:
        try:
            return Course.objects.get(course_id=course_id), None
        except Course.DoesNotExist:
            return None, Response(
                {"detail": "Курс не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
    return None, Response(
        {"detail": "Не указан ID или slug курса"},
        status=status.HTTP_400_BAD_REQUEST,
    )


def require_course_author(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        request = _extract_request(args)
        if request is None or not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Требуется авторизация"}, status=status.HTTP_401_UNAUTHORIZED
            )

        if request.user.is_moderator():
            return view_func(*args, **kwargs)

        course, error = _get_course_from_kwargs(kwargs)
        if error is not None:
            return error

        if not request.user.is_course_author(course):
            return Response(
                {"detail": "Доступ запрещен. Вы не автор этого курса"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return view_func(*args, **kwargs)

    return wrapper


def require_course_enrollment(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        request = _extract_request(args)
        if request is None or not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Требуется авторизация"}, status=status.HTTP_401_UNAUTHORIZED
            )

        if request.user.is_moderator():
            return view_func(*args, **kwargs)

        course_slug = kwargs.get("course_slug") or kwargs.get("slug")
        if not course_slug:
            return Response({"detail": "Не указан slug курса"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            course = Course.objects.get(slug=course_slug)
        except Course.DoesNotExist:
            return Response({"detail": "Курс не найден"}, status=status.HTTP_404_NOT_FOUND)

        if request.user.is_course_author(course):
            return view_func(*args, **kwargs)

        if not request.user.is_enrolled(course):
            return Response(
                {"detail": "Вы не записаны на этот курс"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return view_func(*args, **kwargs)

    return wrapper
