from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from ...models import Course, Homework, Lesson, Section


def lesson_queryset_for_course(course_slug, include_drafts=False):
    hw_qs = Homework.objects.order_by('homework_number', 'created_at')
    if not include_drafts:
        hw_qs = hw_qs.filter(type=Homework.PUBLISHED_STATUS)

    qs = (
        Lesson.objects.filter(section__course__slug=course_slug)
        .select_related('section', 'section__course')
    )
    if not include_drafts:
        qs = qs.filter(
            type=Lesson.PUBLISHED_STATUS,
            section__type=Section.PUBLISHED_STATUS,
            section__course__type=Course.PUBLISHED_STATUS,
        )
    return qs.prefetch_related(
        Prefetch('homework_set', queryset=hw_qs),
        'webinar__recordings',
    ).order_by('lesson_number')


def homework_queryset_for_lesson(course_slug, lesson_slug, include_drafts=False):
    qs = (
        Homework.objects.filter(
            lesson__slug=lesson_slug,
            lesson__section__course__slug=course_slug,
        )
        .select_related('lesson')
        .prefetch_related('question_set', 'task_set')
    )
    if not include_drafts:
        qs = qs.filter(
            type=Homework.PUBLISHED_STATUS,
            lesson__type=Lesson.PUBLISHED_STATUS,
            lesson__section__type=Section.PUBLISHED_STATUS,
            lesson__section__course__type=Course.PUBLISHED_STATUS,
        )
    return qs.order_by('homework_number')


def get_lesson_or_404(course_slug, lesson_slug, include_drafts=False):
    return get_object_or_404(
        lesson_queryset_for_course(course_slug, include_drafts=include_drafts),
        slug=lesson_slug,
    )


def get_homework_or_404(course_slug, lesson_slug, homework_slug, include_drafts=False):
    return get_object_or_404(
        homework_queryset_for_lesson(course_slug, lesson_slug, include_drafts=include_drafts),
        slug=homework_slug,
    )
