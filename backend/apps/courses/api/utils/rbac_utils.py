from django.db.models import Q

from ...models import Course, Homework, Lesson, Section


def user_sees_course_drafts(user, course):
    if user.is_moderator():
        return True
    if user.is_teacher() and user.is_course_author(course):
        return True
    return False


class CourseContentVisibility:

    def __init__(self, user, course):
        self.user = user
        self.course = course
        self.is_moderator = user.is_moderator()
        self.is_author = user.is_teacher() and user.is_course_author(course)
        self.see_drafts = self.is_moderator or self.is_author
        self.include_drafts = self.see_drafts
        self.cache_scope = 'all' if self.see_drafts else 'pub'
        self.show_types_in_tree = self.is_moderator or self.is_author

    def has_course_home_access(self):
        return (
            self.user.is_enrolled(self.course)
            or self.is_author
            or self.is_moderator
        )


def course_content_visibility(user, course):
    return CourseContentVisibility(user, course)


def draft_visibility_for_course(user, course):
    return course_content_visibility(user, course)


def published_lesson_hierarchy_q(lesson_field_prefix='lesson__'):
    return Q(**{
        f'{lesson_field_prefix}section__course__type': Course.PUBLISHED_STATUS,
        f'{lesson_field_prefix}section__type': Section.PUBLISHED_STATUS,
        f'{lesson_field_prefix}type': Lesson.PUBLISHED_STATUS,
    })


def filter_homework_queryset_for_visibility(qs, include_drafts):
    if include_drafts:
        return qs
    return qs.filter(type=Homework.PUBLISHED_STATUS)
