from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.test import TestCase

from apps.applications.api.serializers import (
    ApplicationReviewedSerializer,
    CourseApplicationSerializer,
)
from apps.applications.models import CourseApplication
from apps.courses.tests.test_models import create_test_course, create_test_user


class CourseApplicationModelTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="app_model_st@test.local", role="student")
        self.moderator = create_test_user(email="app_model_mod@test.local", role="moderator")
        self.course = create_test_course(title="App Model Course")

    def test_application_default_status_pending(self):
        app = CourseApplication.objects.create(user=self.student, course=self.course)
        self.assertEqual(app.status, CourseApplication.PENDING)

    def test_application_str_contains_user_course_status(self):
        app = CourseApplication.objects.create(user=self.student, course=self.course)
        s = str(app)
        self.assertIn("pending", s)

    def test_application_unique_per_user_and_course(self):
        CourseApplication.objects.create(user=self.student, course=self.course)
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                CourseApplication.objects.create(user=self.student, course=self.course)

    def test_application_cascade_deleted_with_user(self):
        app = CourseApplication.objects.create(user=self.student, course=self.course)
        aid = app.application_id
        self.student.delete()
        self.assertFalse(CourseApplication.objects.filter(application_id=aid).exists())

    def test_application_cascade_deleted_with_course(self):
        app = CourseApplication.objects.create(user=self.student, course=self.course)
        aid = app.application_id
        self.course.delete()
        self.assertFalse(CourseApplication.objects.filter(application_id=aid).exists())

    def test_application_reviewed_by_set_null_on_moderator_delete(self):
        app = CourseApplication.objects.create(
            user=self.student, course=self.course, reviewed_by=self.moderator
        )
        self.moderator.delete()
        app.refresh_from_db()
        self.assertIsNone(app.reviewed_by)

    def test_application_status_choices(self):
        statuses = [s[0] for s in CourseApplication.STATUS_CHOICES]
        self.assertIn(CourseApplication.PENDING, statuses)
        self.assertIn(CourseApplication.APPROVED, statuses)
        self.assertIn(CourseApplication.REJECTED, statuses)

    def test_approved_application_status(self):
        app = CourseApplication.objects.create(user=self.student, course=self.course)
        app.status = CourseApplication.APPROVED
        app.save()
        app.refresh_from_db()
        self.assertEqual(app.status, CourseApplication.APPROVED)

    def test_rejected_application_status(self):
        app = CourseApplication.objects.create(user=self.student, course=self.course)
        app.status = CourseApplication.REJECTED
        app.save()
        app.refresh_from_db()
        self.assertEqual(app.status, CourseApplication.REJECTED)


class CourseApplicationSerializerTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="app_ser_st@test.local", role="student")
        self.course = create_test_course(title="App Serializer Course")
        self.app = CourseApplication.objects.create(user=self.student, course=self.course)

    def test_serializer_includes_all_required_fields(self):
        data = CourseApplicationSerializer(self.app).data
        for field in ("application_id", "status", "created_at", "updated_at", "user"):
            self.assertIn(field, data)

    def test_serializer_user_nested_includes_email(self):
        data = CourseApplicationSerializer(self.app).data
        user_data = data["user"]
        self.assertIn("email", user_data)
        self.assertIsNotNone(user_data["email"])

    def test_serializer_user_nested_includes_names(self):
        data = CourseApplicationSerializer(self.app).data
        user_data = data["user"]
        self.assertIn("first_name", user_data)
        self.assertIn("last_name", user_data)

    def test_serializer_status_is_pending_by_default(self):
        data = CourseApplicationSerializer(self.app).data
        self.assertEqual(data["status"], CourseApplication.PENDING)


class ApplicationReviewedSerializerTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="app_rev_ser_st@test.local", role="student")
        self.course = create_test_course(title="Rev Serializer Course")
        self.app = CourseApplication.objects.create(user=self.student, course=self.course)

    def test_reviewed_serializer_includes_required_fields(self):
        data = ApplicationReviewedSerializer(self.app).data
        for field in ("application_id", "status", "reviewed_at", "reviewed_by"):
            self.assertIn(field, data)

    def test_reviewed_serializer_all_fields_read_only(self):
        serializer = ApplicationReviewedSerializer(data={"status": "approved"})
        serializer.is_valid()
        self.assertEqual(serializer.validated_data, {})
