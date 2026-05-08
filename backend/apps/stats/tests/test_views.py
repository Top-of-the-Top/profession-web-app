from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.courses.models import Course, Lesson, PublishableMixin, PurchasedCourse, Section
from apps.payments.models import Payment
from apps.stats.models import RecordingView, WebinarAttendance
from apps.users.models import User
from apps.webinars.models import Recording, Webinar


class HeartbeatViewsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email_cipher="s@x", password="p")
        self.author = User.objects.create_user(
            email_cipher="t@x", password="p", role=User.ROLE_TEACHER
        )
        self.course = Course.objects.create(
            title="C", sub_title="s", description="d", price=0
        )
        self.course.authors.add(self.author)
        section = Section.objects.create(course=self.course, title="S")
        self.lesson = Lesson.objects.create(section=section, title="L")
        self.webinar = Webinar.objects.create(lesson=self.lesson)
        self.recording = Recording.objects.create(
            webinar=self.webinar, duration_seconds=600
        )

    def test_webinar_heartbeat_creates_attendance(self):
        self.client.force_authenticate(self.author)
        url = reverse("webinar-heartbeat", kwargs={"webinar_id": self.webinar.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(WebinarAttendance.objects.filter(user=self.author).count(), 1)

    def test_recording_heartbeat_updates_position(self):
        self.client.force_authenticate(self.author)
        url = reverse("recording-heartbeat", kwargs={"recording_id": self.recording.pk})
        resp = self.client.post(url, {"current_position": 120}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        view = RecordingView.objects.get(user=self.author, recording=self.recording)
        self.assertEqual(view.last_position, 120)
        self.assertEqual(view.watched_seconds, 120)


class CourseHomeMetaTest(APITestCase):
    def setUp(self):
        pub = PublishableMixin.PUBLISHED_STATUS

        self.author = User.objects.create_user(
            email_cipher="t1", password="p", role=User.ROLE_TEACHER
        )
        self.moderator = User.objects.create_user(
            email_cipher="m1", password="p", role=User.ROLE_MODERATOR
        )
        self.student = User.objects.create_user(
            email_cipher="s1", password="p", role=User.ROLE_STUDENT
        )

        self.course = Course.objects.create(
            title="Курс", sub_title="s", description="d", price=0, type=pub,
        )
        self.course.authors.add(self.author)

        section = Section.objects.create(course=self.course, title="С1", type=pub)
        self.lesson = Lesson.objects.create(section=section, title="У1", type=pub)

        payment = Payment.objects.create(user=self.student, total_sum=0, status="success")
        PurchasedCourse.objects.create(
            user=self.student,
            course=self.course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )

    def _get_home(self, user):
        self.client.force_authenticate(user)
        url = reverse(
            "courses:course-homepage", kwargs={"course_slug": self.course.slug}
        )
        return self.client.get(url)

    def test_student_meta_has_progress_fields(self):
        resp = self._get_home(self.student)
        self.assertEqual(resp.status_code, 200)
        meta = resp.data["meta"]
        self.assertEqual(meta["role"], "student")
        self.assertIn("lessons_completed", meta)
        self.assertIn("lessons_total", meta)
        self.assertIn("homeworks_submitted", meta)
        self.assertIn("homeworks_total", meta)
        self.assertIn("attendance_streak", meta)

    def test_teacher_meta_has_aggregate_fields(self):
        resp = self._get_home(self.author)
        self.assertEqual(resp.status_code, 200)
        meta = resp.data["meta"]
        self.assertIn("webinar_attendance_rate", meta)
        self.assertIn("homework_completion_rate", meta)

    def test_moderator_meta_has_aggregate_fields(self):
        resp = self._get_home(self.moderator)
        self.assertEqual(resp.status_code, 200)
        meta = resp.data["meta"]
        self.assertIn("webinar_attendance_rate", meta)
        self.assertIn("homework_completion_rate", meta)

    def test_is_completed_only_for_student(self):
        resp = self._get_home(self.author)
        for section in resp.data["content"]:
            self.assertIsNone(section["section_completed"])
            for lesson in section["lessons"]:
                self.assertIsNone(lesson["is_completed"])

    def test_is_completed_for_student_returns_bool(self):
        resp = self._get_home(self.student)
        for section in resp.data["content"]:
            self.assertIsInstance(section["section_completed"], bool)
            for lesson in section["lessons"]:
                self.assertIsInstance(lesson["is_completed"], bool)


class LessonDetailMetaTest(APITestCase):
    def setUp(self):
        pub = PublishableMixin.PUBLISHED_STATUS

        self.author = User.objects.create_user(
            email_cipher="t2", password="p", role=User.ROLE_TEACHER
        )
        self.student = User.objects.create_user(
            email_cipher="s2", password="p", role=User.ROLE_STUDENT
        )
        self.course = Course.objects.create(
            title="Курс2", sub_title="s", description="d", price=0, type=pub,
        )
        self.course.authors.add(self.author)
        section = Section.objects.create(course=self.course, title="С", type=pub)
        self.lesson = Lesson.objects.create(section=section, title="У", type=pub)

        payment = Payment.objects.create(user=self.student, total_sum=0, status="success")
        PurchasedCourse.objects.create(
            user=self.student,
            course=self.course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )

    def _get_lesson(self, user):
        self.client.force_authenticate(user)
        url = reverse(
            "courses:course-lessons-detail",
            kwargs={"course_slug": self.course.slug, "lesson_slug": self.lesson.slug},
        )
        return self.client.get(url)

    def test_student_lesson_meta_has_progress(self):
        resp = self._get_lesson(self.student)
        self.assertEqual(resp.status_code, 200)
        meta = resp.data["meta"]
        self.assertEqual(meta["role"], "student")
        self.assertIn("watched_ratio", meta)
        self.assertIn("homeworks_submitted", meta)
        self.assertIn("homeworks_total", meta)
        self.assertIn("is_completed", meta)

    def test_teacher_lesson_meta_has_aggregate(self):
        resp = self._get_lesson(self.author)
        self.assertEqual(resp.status_code, 200)
        meta = resp.data["meta"]
        self.assertIn("attended_count", meta)
        self.assertIn("attended_total", meta)
        self.assertIn("homework_submitted_count", meta)
        self.assertIn("homework_submitted_total", meta)


class StatsRoutesAccessTest(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            email_cipher="acc_s", password="p", role=User.ROLE_STUDENT,
        )
        self.teacher_with_course = User.objects.create_user(
            email_cipher="acc_t1", password="p", role=User.ROLE_TEACHER,
        )
        self.teacher_no_course = User.objects.create_user(
            email_cipher="acc_t2", password="p", role=User.ROLE_TEACHER,
        )
        self.moderator = User.objects.create_user(
            email_cipher="acc_m", password="p", role=User.ROLE_MODERATOR,
        )

        self.course = Course.objects.create(
            title="Курс", sub_title="s", description="d", price=0,
        )
        self.course.authors.add(self.teacher_with_course)

    def _get(self, user, name, **kwargs):
        self.client.force_authenticate(user)
        return self.client.get(reverse(name, kwargs=kwargs))

    def test_student_cannot_open_webinars(self):
        resp = self._get(self.student, "stats-webinars")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_without_authored_course_cannot_open(self):
        resp = self._get(self.teacher_no_course, "stats-webinars")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_with_course_can_open(self):
        resp = self._get(self.teacher_with_course, "stats-webinars")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_moderator_can_open(self):
        resp = self._get(self.moderator, "stats-webinars")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_students_list_accessible_to_teacher_with_course(self):
        resp = self._get(self.teacher_with_course, "stats-students")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_students_list_forbidden_for_student(self):
        resp = self._get(self.student, "stats-students")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_card_forbidden_for_teacher_not_author(self):
        resp = self._get(
            self.teacher_no_course,
            "stats-student-card",
            user_id=self.student.pk,
            course_id=self.course.pk,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_card_ok_for_author(self):
        resp = self._get(
            self.teacher_with_course,
            "stats-student-card",
            user_id=self.student.pk,
            course_id=self.course.pk,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["student_id"], self.student.pk)

    def test_school_courses_forbidden_for_teacher(self):
        resp = self._get(self.teacher_with_course, "stats-school-courses")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_school_courses_ok_for_moderator(self):
        resp = self._get(self.moderator, "stats-school-courses")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_school_teachers_forbidden_for_teacher(self):
        resp = self._get(self.teacher_with_course, "stats-school-teachers")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_school_teachers_ok_for_moderator(self):
        resp = self._get(self.moderator, "stats-school-teachers")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
