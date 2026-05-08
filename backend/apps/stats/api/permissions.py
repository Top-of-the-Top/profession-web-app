from rest_framework.permissions import BasePermission


class IsEnrolledOrCourseStaff(BasePermission):
    message = "Нет доступа к статистике этого курса"

    def has_object_permission(self, request, view, obj):
        course = _resolve_course(obj)
        user = request.user
        if user.is_moderator():
            return True
        if user.is_course_author(course):
            return True
        return user.is_enrolled(course)


def _resolve_course(obj):
    from apps.courses.models import Course, Lesson
    from apps.stats.models import LessonProgress
    from apps.webinars.models import Recording, Webinar

    if isinstance(obj, Course):
        return obj
    if isinstance(obj, Lesson):
        return obj.section.course
    if isinstance(obj, Webinar):
        return obj.lesson.section.course
    if isinstance(obj, Recording):
        return obj.webinar.lesson.section.course
    if isinstance(obj, LessonProgress):
        return obj.lesson.section.course
    raise ValueError(f"Не умею определять course для {type(obj).__name__}")


class IsTeacherAuthorOrModerator(BasePermission):
    message = "Доступ к статистике только для преподавателей и модераторов"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_moderator():
            return True
        if user.is_teacher() and user.authored_courses.exists():
            return True
        return False
    