from django.core.cache import caches
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.tests.test_models import BaseTestCase, create_test_course, create_test_user
from apps.users.api.utils.token_utils import get_tokens_for_user


class SpecialCourseVisibilityTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        caches["default"].clear()
        self.client = APIClient()
        self.student = create_test_user(email="vis_student@test.com", role="student")
        self.teacher = create_test_user(email="vis_teacher@test.com", role="teacher")
        self.moderator = create_test_user(email="vis_mod@test.com", role="moderator")

        self.normal_course = create_test_course(title="Normal Course", price=100)
        self.special_course = create_test_course(title="Special Course", price=0)
        self.special_course.is_special = True
        self.special_course.save(update_fields=["is_special"])
        self.special_course.authors.add(self.teacher)

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_special_course_hidden_from_landing(self):
        r = self.client.get("/api/v1/landing/courses/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        slugs = [c["slug"] for c in r.data["data"]]
        self.assertNotIn(self.special_course.slug, slugs)
        self.assertIn(self.normal_course.slug, slugs)

    def test_special_course_hidden_from_student_course_list(self):
        self._auth(self.student)
        r = self.client.get("/api/v1/courses/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        slugs = [c["slug"] for c in r.data]
        self.assertNotIn(self.special_course.slug, slugs)
        self.assertIn(self.normal_course.slug, slugs)

    def test_special_course_visible_to_moderator_in_course_list(self):
        self._auth(self.moderator)
        r = self.client.get("/api/v1/courses/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        slugs = [c["slug"] for c in r.data]
        self.assertIn(self.special_course.slug, slugs)

    def test_special_course_visible_to_author_in_course_list(self):
        self._auth(self.teacher)
        r = self.client.get("/api/v1/courses/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        slugs = [c["slug"] for c in r.data]
        self.assertIn(self.special_course.slug, slugs)

    def test_special_course_detail_returns_404_for_unauthenticated(self):
        r = self.client.get(f"/api/v1/courses/{self.special_course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_special_course_detail_returns_404_for_student_without_enrollment(self):
        self._auth(self.student)
        r = self.client.get(f"/api/v1/courses/{self.special_course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_special_course_detail_accessible_to_author(self):
        self._auth(self.teacher)
        r = self.client.get(f"/api/v1/courses/{self.special_course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["is_special"])

    def test_special_course_detail_accessible_to_moderator(self):
        self._auth(self.moderator)
        r = self.client.get(f"/api/v1/courses/{self.special_course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
