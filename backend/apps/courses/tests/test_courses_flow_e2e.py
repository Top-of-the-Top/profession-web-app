import tempfile
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.payments.models import Payment
from apps.users.api.utils.token_utils import get_tokens_for_user

from ..models import Course, Homework, PurchasedCourse
from .test_models import (
    BaseTestCase,
    create_test_homework,
    create_test_lesson,
    create_test_section,
    create_test_user,
    publish_course_tree,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CoursesPublishedStudentFlowE2eTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_post_course_publish_content_enroll_then_student_reads_api(self):
        moderator = create_test_user(email="moderator_flow@test.com", role="moderator")
        teacher = create_test_user(email="teacher_flow@test.com", role="teacher")
        self._auth(moderator)
        created = self.client.post(
            "/api/v1/courses/",
            {
                "title": "Flow Course",
                "sub_title": "Sub",
                "description": "Body",
                "price": 3000,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        slug = created.data["slug"]
        course = Course.objects.get(slug=slug)
        course.authors.add(teacher)
        section = create_test_section(course, title="Flow Section")
        lesson = create_test_lesson(section, title="Flow Lesson")
        create_test_homework(lesson, title="Flow HW")
        publish_course_tree(course)

        student = create_test_user(email="student_flow@test.com", role="student")
        payment = Payment.objects.create(user=student, total_sum=3000, status="success")
        PurchasedCourse.objects.create(
            user=student,
            course=course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )
        self._auth(student)
        homework = Homework.objects.get(lesson=lesson)
        urls = [
            f"/api/v1/courses/{slug}/",
            f"/api/v1/courses/{slug}/home/",
            f"/api/v1/courses/{slug}/lessons/{lesson.slug}/",
            f"/api/v1/courses/{slug}/lessons/{lesson.slug}/homeworks/{homework.slug}/",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
