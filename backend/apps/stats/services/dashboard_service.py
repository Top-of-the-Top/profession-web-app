import logging
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.stats.services.progress_service import (
    SUBMITTED_STATUSES,
    _active_purchaser_ids,
    _course_homework_completion_rate,
    _course_webinar_attendance_rate,
    _webinar_duration_seconds,
)

logger = logging.getLogger(__name__)


def list_webinars_table(*, requester, course_title=None, date_from=None, date_to=None):
    from apps.stats.models import LessonProgress, WebinarAttendance
    from apps.stats.services.progress_service import WEBINAR_THRESHOLD
    from apps.users.models import User
    from apps.webinars.models import Webinar

    qs = Webinar.objects.filter(ended_at__isnull=False).select_related("lesson__section__course")
    if not requester.is_moderator():
        qs = qs.filter(lesson__section__course__authors=requester)
    if course_title:
        qs = qs.filter(lesson__section__course__title__icontains=course_title)
    if date_from:
        qs = qs.filter(ended_at__gte=date_from)
    if date_to:
        qs = qs.filter(ended_at__lte=date_to)

    rows = []
    for webinar in qs.order_by("-ended_at").distinct():
        course = webinar.lesson.section.course
        active = _active_purchaser_ids(course)

        attended_any_ids = set(
            WebinarAttendance.objects.filter(webinar=webinar, user_id__in=active)
            .values_list("user_id", flat=True)
            .distinct()
        )

        attended_threshold_ids = set(
            LessonProgress.objects.filter(
                lesson=webinar.lesson,
                user_id__in=active,
                watched_ratio__gte=WEBINAR_THRESHOLD,
            ).values_list("user_id", flat=True)
        )

        hw_submitted_ids = set(
            LessonProgress.objects.filter(
                lesson=webinar.lesson,
                user_id__in=active,
                all_homeworks_submitted=True,
            ).values_list("user_id", flat=True)
        )

        relevant_ids = attended_any_ids | attended_threshold_ids | hw_submitted_ids
        users_by_id = {
            u.pk: u
            for u in User.objects.filter(pk__in=relevant_ids).only(
                "pk",
                "first_name",
                "last_name",
            )
        }

        rows.append(
            {
                "webinar_id": str(webinar.pk),
                "course_title": course.title,
                "course_slug": course.slug,
                "lesson_title": webinar.lesson.title,
                "started_at": webinar.started_at,
                "ended_at": webinar.ended_at,
                "attended_total": len(active),
                "attended_any": len(attended_any_ids),
                "attended_threshold": len(attended_threshold_ids),
                "homework_submitted_count": len(hw_submitted_ids),
                "attended_any_users": _users_brief(attended_any_ids, users_by_id),
                "attended_threshold_users": _users_brief(attended_threshold_ids, users_by_id),
                "homework_submitted_users": _users_brief(hw_submitted_ids, users_by_id),
            }
        )
    return rows


def _users_brief(user_ids, users_by_id):
    rows = []
    for uid in user_ids:
        user = users_by_id.get(uid)
        if user is None:
            continue
        full_name = f"{user.first_name} {user.last_name}".strip() or "—"
        rows.append({"user_id": user.pk, "full_name": full_name})
    rows.sort(key=lambda r: r["full_name"])
    return rows


def list_students(*, requester, course_title=None, query=None):
    from apps.courses.models import CourseEnrollment
    from apps.users.api.utils.crypto_utils import decrypt_data
    from apps.users.models import User

    purchases = CourseEnrollment.objects.select_related("course", "user").filter(
        access_expires_at__gt=timezone.now(),
        user__role=User.ROLE_STUDENT,
    )
    if not requester.is_moderator():
        purchases = purchases.filter(course__authors=requester)
    if course_title:
        purchases = purchases.filter(course__title__icontains=course_title)

    by_user = {}
    for purchase in purchases:
        u = purchase.user
        item = by_user.setdefault(
            u.pk,
            {
                "user_id": u.pk,
                "full_name": f"{u.first_name} {u.last_name}".strip() or "—",
                "email": decrypt_data(u.email_cipher) if u.email_cipher else "",
                "phone": decrypt_data(u.phone_cipher) if u.phone_cipher else "",
                "courses": [],
            },
        )
        item["courses"].append(
            {
                "course_id": str(purchase.course.pk),
                "course_slug": purchase.course.slug,
                "title": purchase.course.title,
            }
        )

    rows = list(by_user.values())
    if query:
        q = query.lower()
        rows = [
            r
            for r in rows
            if q in r["full_name"].lower() or q in r["email"].lower() or q in r["phone"].lower()
        ]
    return rows


def student_card(*, requester, student_id, course_slug):
    from apps.courses.models import Course, Lesson, PublishableMixin
    from apps.homeworks.models import Attempt
    from apps.stats.models import LessonProgress
    from apps.users.models import User

    try:
        course = Course.objects.get(slug=course_slug)
    except Course.DoesNotExist:
        return None
    if not requester.is_moderator() and not requester.is_course_author(course):
        return None

    try:
        student = User.objects.get(pk=student_id)
    except User.DoesNotExist:
        return None

    pub = PublishableMixin.PUBLISHED_STATUS

    lessons = (
        Lesson.objects.filter(section__course=course, type=pub, section__type=pub)
        .select_related("section")
        .prefetch_related("homework_set")
        .order_by("section__section_number", "lesson_number")
    )

    rows = []
    for lesson in lessons:
        webinar = getattr(lesson, "webinar", None)
        webinar_info = _student_webinar_info(student, webinar)

        homeworks = []
        submitted = 0
        published_homeworks = list(lesson.homework_set.filter(type=pub))
        for hw in published_homeworks:
            attempt = Attempt.objects.filter(user=student, homework=hw).first()
            status = "not_started" if attempt is None else attempt.status
            if status in SUBMITTED_STATUSES:
                submitted += 1
            homeworks.append(
                {
                    "homework_id": str(hw.pk),
                    "title": hw.title,
                    "status": status,
                    "grade": (
                        attempt.grade if attempt and status == Attempt.REVIEWED_STATUS else None
                    ),
                }
            )

        progress = LessonProgress.objects.filter(user=student, lesson=lesson).first()
        rows.append(
            {
                "lesson_id": str(lesson.pk),
                "lesson_title": lesson.title,
                "webinar": webinar_info,
                "homeworks": homeworks,
                "homeworks_submitted": submitted,
                "homeworks_total": len(published_homeworks),
                "is_completed": bool(progress and progress.is_completed),
            }
        )

    return {
        "student_id": student.pk,
        "course_id": str(course.pk),
        "lessons": rows,
    }


def _student_webinar_info(student, webinar):
    from apps.stats.models import RecordingView, WebinarAttendance

    if webinar is None:
        return None

    duration = _webinar_duration_seconds(webinar)
    if duration > 0:
        live_seconds = (
            WebinarAttendance.objects.filter(user=student, webinar=webinar).aggregate(
                total=Sum("watched_seconds")
            )["total"]
        ) or 0
        live_ratio = min(live_seconds / duration, 1.0)
    else:
        live_ratio = 0.0

    best_rec_ratio = 0.0
    rec_views = RecordingView.objects.filter(
        user=student, recording__webinar=webinar
    ).select_related("recording")
    for view in rec_views:
        rec = view.recording
        if rec.is_deleted or not rec.duration_seconds:
            continue
        ratio = min(view.watched_seconds / rec.duration_seconds, 1.0)
        if ratio > best_rec_ratio:
            best_rec_ratio = ratio

    if live_ratio == 0 and best_rec_ratio == 0:
        return {"kind": "none", "watched_ratio": 0.0}
    if live_ratio >= best_rec_ratio:
        return {"kind": "live", "watched_ratio": round(live_ratio, 2)}
    return {"kind": "recording", "watched_ratio": round(best_rec_ratio, 2)}


def school_courses_table():
    from apps.courses.models import Course, PublishableMixin
    from apps.stats.models import LessonProgress

    pub = PublishableMixin.PUBLISHED_STATUS
    rows = []
    for course in Course.objects.all():
        active = _active_purchaser_ids(course)
        if not active:
            rows.append(
                {
                    "course_id": str(course.pk),
                    "title": course.title,
                    "students": 0,
                    "avg_progress": 0.0,
                    "avg_attendance": 0.0,
                    "avg_homework": 0.0,
                }
            )
            continue

        lessons_total = sum(
            section.lesson_set.filter(type=pub).count()
            for section in course.section_set.filter(type=pub)
        )
        if lessons_total == 0:
            avg_progress = 0.0
        else:
            completed = LessonProgress.objects.filter(
                user_id__in=active,
                lesson__section__course=course,
                lesson__type=pub,
                lesson__section__type=pub,
                is_completed=True,
            ).count()
            avg_progress = completed / (lessons_total * len(active))

        rows.append(
            {
                "course_id": str(course.pk),
                "title": course.title,
                "students": len(active),
                "avg_progress": round(avg_progress, 2),
                "avg_attendance": round(_course_webinar_attendance_rate(course), 2),
                "avg_homework": round(_course_homework_completion_rate(course), 2),
            }
        )
    return rows


def school_teachers_table():
    from apps.homeworks.models import Attempt
    from apps.users.models import User

    now = timezone.now()
    rows = []
    for teacher in User.objects.filter(role=User.ROLE_TEACHER).order_by("first_name", "last_name"):
        reviewed = Attempt.objects.filter(reviewed_by=teacher, reviewed_at__isnull=False)
        rows.append(
            {
                "user_id": teacher.pk,
                "full_name": f"{teacher.first_name} {teacher.last_name}".strip() or "—",
                "reviewed_7d": reviewed.filter(reviewed_at__gte=now - timedelta(days=7)).count(),
                "reviewed_30d": reviewed.filter(reviewed_at__gte=now - timedelta(days=30)).count(),
                "last_login": teacher.last_login,
            }
        )
    return rows
