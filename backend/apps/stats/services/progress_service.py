import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.stats.models import RecordingView, WebinarAttendance
from apps.webinars.models import Webinar

logger = logging.getLogger(__name__)

WEBINAR_THRESHOLD = getattr(settings, "STATISTICS_WEBINAR_THRESHOLD", 0.7)
SUBMITTED_STATUSES = ("submitted", "reviewed")

HEARTBEAT_INTERVAL_SECONDS = 30
HEARTBEAT_TIMEOUT = timedelta(seconds=HEARTBEAT_INTERVAL_SECONDS * 3)

HEARTBEAT_MAX_GROWTH_SECONDS = HEARTBEAT_INTERVAL_SECONDS * 2

CACHE_TTL_SECONDS = 30


class WebinarAttendanceService:
    @staticmethod
    @transaction.atomic
    def heartbeat(*, user, webinar: Webinar, now=None):
        now = now or timezone.now()

        recent = (
            WebinarAttendance.objects.select_for_update()
            .filter(user=user, webinar=webinar)
            .order_by("-joined_at")
            .first()
        )

        if recent is not None and recent.left_at and (now - recent.left_at) <= HEARTBEAT_TIMEOUT:
            delta = (now - recent.left_at).total_seconds()
            growth = min(int(delta), HEARTBEAT_MAX_GROWTH_SECONDS)
            recent.watched_seconds += growth
            recent.left_at = now
            recent.save(update_fields=["watched_seconds", "left_at", "updated_at"])
            attendance = recent
        elif recent is not None and not recent.left_at:
            delta = (now - recent.joined_at).total_seconds()
            growth = min(int(delta), HEARTBEAT_MAX_GROWTH_SECONDS)
            recent.watched_seconds += growth
            recent.left_at = now
            recent.save(update_fields=["watched_seconds", "left_at", "updated_at"])
            attendance = recent
        else:
            attendance = WebinarAttendance.objects.create(
                user=user,
                webinar=webinar,
                joined_at=now,
                left_at=now,
                watched_seconds=0,
            )
            logger.info(
                "Новая сессия посещения вебинара: user=%s webinar=%s",
                user.pk,
                webinar.pk,
            )

        total = (
            WebinarAttendance.objects.filter(user=user, webinar=webinar).aggregate(
                total=Sum("watched_seconds")
            )["total"]
        ) or 0
        return attendance, total


ANTIFRAUD_MAX_RATE = 1.5


class RecordingViewService:
    @staticmethod
    @transaction.atomic
    def heartbeat(*, user, recording, current_position: int, now=None):
        now = now or timezone.now()

        view, created = RecordingView.objects.select_for_update().get_or_create(
            user=user,
            recording=recording,
            defaults={
                "watched_seconds": current_position,
                "last_position": current_position,
            },
        )

        if not created and current_position > view.watched_seconds:
            growth = current_position - view.watched_seconds
            elapsed = (now - view.updated_at).total_seconds()
            allowed_growth = max(int(elapsed * ANTIFRAUD_MAX_RATE), 0)
            if growth > allowed_growth:
                logger.warning(
                    "Подозрительный рост watched_seconds: "
                    "user=%s recording=%s growth=%s elapsed=%.1f",
                    user.pk,
                    recording.pk,
                    growth,
                    elapsed,
                )
                view.watched_seconds += allowed_growth
            else:
                view.watched_seconds = current_position

        view.last_position = current_position
        view.save(update_fields=["watched_seconds", "last_position", "updated_at"])
        return view


def recompute_lesson_progress(*, user, lesson):
    from apps.homeworks.models import Attempt
    from apps.stats.models import LessonProgress
    from apps.webinars.models import Webinar

    webinar = Webinar.objects.filter(lesson=lesson).first()

    watched_ratio = _calc_watched_ratio(user=user, webinar=webinar)

    homeworks = list(lesson.homework_set.all())
    if not homeworks:
        all_homeworks_submitted = True
    else:
        submitted_count = Attempt.objects.filter(
            user=user,
            homework__in=homeworks,
            status__in=SUBMITTED_STATUSES,
        ).count()
        all_homeworks_submitted = submitted_count == len(homeworks)

    if webinar is None:
        webinar_done = True
    else:
        webinar_done = watched_ratio >= WEBINAR_THRESHOLD

    is_completed = webinar_done and all_homeworks_submitted

    progress, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    was_completed = progress.is_completed

    progress.watched_ratio = watched_ratio
    progress.all_homeworks_submitted = all_homeworks_submitted
    progress.is_completed = is_completed
    if is_completed and not was_completed:
        progress.completed_at = timezone.now()
    progress.save()

    logger.info(
        "Пересчитан прогресс по уроку: user=%s lesson=%s watched=%.2f hw=%s done=%s",
        user.pk,
        lesson.pk,
        watched_ratio,
        all_homeworks_submitted,
        is_completed,
    )
    return progress


def _calc_watched_ratio(*, user, webinar):
    from apps.stats.models import RecordingView, WebinarAttendance

    if webinar is None:
        return 0.0

    webinar_duration = _webinar_duration_seconds(webinar)
    if webinar_duration > 0:
        live_watched = WebinarAttendance.objects.filter(user=user, webinar=webinar).values_list(
            "watched_seconds", flat=True
        )
        live_ratio = min(sum(live_watched) / webinar_duration, 1.0)
    else:
        live_ratio = 0.0

    recording_ratio = 0.0
    views = RecordingView.objects.filter(user=user, recording__webinar=webinar).select_related(
        "recording"
    )
    for view in views:
        rec = view.recording
        if rec.is_deleted or not rec.duration_seconds:
            continue
        ratio = min(view.watched_seconds / rec.duration_seconds, 1.0)
        if ratio > recording_ratio:
            recording_ratio = ratio

    return max(live_ratio, recording_ratio)


def _webinar_duration_seconds(webinar):
    if webinar.started_at and webinar.ended_at:
        return max(int((webinar.ended_at - webinar.started_at).total_seconds()), 0)
    if webinar.started_at and webinar.status == webinar.LIVE_STATUS:
        return max(int((timezone.now() - webinar.started_at).total_seconds()), 0)
    return 0


def _active_purchaser_ids(course):
    from apps.courses.models import CourseEnrollment

    return list(
        CourseEnrollment.objects.filter(
            course=course, access_expires_at__gt=timezone.now()
        ).values_list("user_id", flat=True)
    )


def _lesson_attended_count(lesson, user_ids):
    from apps.stats.models import LessonProgress

    return LessonProgress.objects.filter(
        lesson=lesson, user_id__in=user_ids, watched_ratio__gte=WEBINAR_THRESHOLD
    ).count()


def _lesson_homework_submitted_count(lesson, user_ids):
    from apps.stats.models import LessonProgress

    return LessonProgress.objects.filter(
        lesson=lesson, user_id__in=user_ids, all_homeworks_submitted=True
    ).count()


def _course_webinar_attendance_rate(course):
    from apps.courses.models import Lesson
    from apps.webinars.models import Webinar

    active_students = _active_purchaser_ids(course)
    if not active_students:
        return 0.0

    lessons_with_webinar = Lesson.objects.filter(
        section__course=course, type="published", section__type="published"
    ).filter(webinar__isnull=False)
    if not lessons_with_webinar.exists():
        return 0.0

    total_rate = 0.0
    count = 0
    for lesson in lessons_with_webinar:
        attended = _lesson_attended_count(lesson, active_students)
        total_rate += attended / len(active_students)
        count += 1
    return total_rate / count if count else 0.0


def _course_homework_completion_rate(course):
    from apps.courses.models import Lesson

    active_students = _active_purchaser_ids(course)
    if not active_students:
        return 0.0

    lessons_with_hw = (
        Lesson.objects.filter(section__course=course, type="published", section__type="published")
        .filter(homework__type="published")
        .distinct()
    )
    if not lessons_with_hw.exists():
        return 0.0

    total_rate = 0.0
    count = 0
    for lesson in lessons_with_hw:
        submitted = _lesson_homework_submitted_count(lesson, active_students)
        total_rate += submitted / len(active_students)
        count += 1
    return total_rate / count if count else 0.0


def _attendance_streak(*, user, course):
    from apps.stats.models import LessonProgress
    from apps.webinars.models import Webinar

    webinars = (
        Webinar.objects.filter(lesson__section__course=course, ended_at__isnull=False)
        .order_by("-ended_at")
        .values_list("lesson_id", flat=True)
    )
    streak = 0
    for lesson_id in webinars:
        progress = LessonProgress.objects.filter(user=user, lesson_id=lesson_id).first()
        if progress and progress.watched_ratio >= WEBINAR_THRESHOLD:
            streak += 1
        else:
            break
    return streak


def course_meta_for_user(*, user, course):
    if user.is_student():
        return _course_meta_student(user=user, course=course)
    if user.is_teacher() or user.is_moderator():
        return _course_meta_staff(course=course)
    return {"role": user.role}


def lesson_meta_for_user(*, user, lesson):
    if user.is_student():
        return _lesson_meta_student(user=user, lesson=lesson)
    if user.is_teacher() or user.is_moderator():
        return _lesson_meta_staff(lesson=lesson)
    return {"role": user.role}


def _course_meta_student(*, user, course):
    from apps.courses.models import Homework, Lesson, PublishableMixin
    from apps.homeworks.models import Attempt
    from apps.stats.models import LessonProgress

    pub = PublishableMixin.PUBLISHED_STATUS

    lessons_total = Lesson.objects.filter(
        section__course=course,
        type=pub,
        section__type=pub,
    ).count()
    lessons_completed = LessonProgress.objects.filter(
        user=user,
        lesson__section__course=course,
        lesson__type=pub,
        lesson__section__type=pub,
        is_completed=True,
    ).count()

    homeworks_total = Homework.objects.filter(
        lesson__section__course=course,
        type=pub,
        lesson__type=pub,
        lesson__section__type=pub,
    ).count()
    homeworks_submitted = Attempt.objects.filter(
        user=user,
        homework__lesson__section__course=course,
        homework__type=pub,
        homework__lesson__type=pub,
        homework__lesson__section__type=pub,
        status__in=SUBMITTED_STATUSES,
    ).count()

    streak = _attendance_streak(user=user, course=course)

    return {
        "role": "student",
        "lessons_completed": lessons_completed,
        "lessons_total": lessons_total,
        "homeworks_submitted": homeworks_submitted,
        "homeworks_total": homeworks_total,
        "attendance_streak": streak,
        "course_rank_top_percent": None,
    }


def _course_meta_staff(*, course):
    cache = caches["default"]
    key = f"default:stats:course_meta:staff:{course.slug}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    data = {
        "role": "teacher_or_moderator",
        "webinar_attendance_rate": _course_webinar_attendance_rate(course),
        "homework_completion_rate": _course_homework_completion_rate(course),
    }
    cache.set(key, data, CACHE_TTL_SECONDS)
    return data


def _lesson_meta_student(*, user, lesson):
    from apps.stats.models import LessonProgress

    progress = LessonProgress.objects.filter(user=user, lesson=lesson).first()
    homeworks_total = lesson.homework_set.filter(type="published").count()
    submitted = (
        lesson.homework_set.filter(
            type="published",
            attempt__user=user,
            attempt__status__in=SUBMITTED_STATUSES,
        )
        .distinct()
        .count()
    )

    return {
        "role": "student",
        "watched_ratio": progress.watched_ratio if progress else 0.0,
        "homeworks_submitted": submitted,
        "homeworks_total": homeworks_total,
        "is_completed": progress.is_completed if progress else False,
    }


def _lesson_meta_staff(*, lesson):
    cache = caches["default"]
    key = f"default:stats:lesson_meta:staff:{lesson.slug}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    course = lesson.section.course
    active_students = _active_purchaser_ids(course)

    data = {
        "role": "teacher_or_moderator",
        "attended_count": _lesson_attended_count(lesson, active_students),
        "attended_total": len(active_students),
        "homework_submitted_count": _lesson_homework_submitted_count(lesson, active_students),
        "homework_submitted_total": len(active_students),
    }
    cache.set(key, data, CACHE_TTL_SECONDS)
    return data


def compute_homework_percentile(*, user, homework):
    from apps.homeworks.models import Attempt

    course = homework.lesson.section.course
    course_students = set(_active_purchaser_ids(course))
    if user.pk not in course_students:
        return None
    course_students.discard(user.pk)
    total = len(course_students)
    if total == 0:
        return None

    user_attempt = Attempt.objects.filter(
        user=user,
        homework=homework,
        status__in=SUBMITTED_STATUSES,
    ).first()
    if user_attempt is None or user_attempt.send_at is None:
        return None

    others = Attempt.objects.filter(homework=homework, user_id__in=course_students).values(
        "user_id", "status", "send_at"
    )
    submitted_other = {
        row["user_id"]: row["send_at"]
        for row in others
        if row["status"] in SUBMITTED_STATUSES and row["send_at"] is not None
    }
    later_or_not_done = 0
    for uid in course_students:
        their_send_at = submitted_other.get(uid)
        if their_send_at is None or their_send_at > user_attempt.send_at:
            later_or_not_done += 1

    return int(round(later_or_not_done / total * 100))
