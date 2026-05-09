from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import Course
from apps.courses.tests.test_models import BaseTestCase, create_test_course, create_test_user
from apps.users.api.utils.token_utils import get_tokens_for_user


class ModeratorCourseAuthorsPublishHttpTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.moderator = create_test_user(email="adm_mod2@test.local", role="moderator")
        self.teacher = create_test_user(email="adm_tc2@test.local", role="teacher")

    def _auth(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(user)['access_token']}"
        )

    @patch("apps.admin_panel.api.views.invalidate_on_course_model_change")
    def test_add_course_author_requires_user_id_query_param(self, mock_inv):
        course = create_test_course(title="ADM Course", sub_title="s", description="d", price=0)
        self._auth(self.moderator)
        url = f"/api/admin-panel/courses/{course.slug}/add-author/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        mock_inv.assert_not_called()

    @patch("apps.admin_panel.api.views.invalidate_on_course_model_change")
    def test_add_course_author_updates_m2m_and_invalidates_course_cache(self, mock_inv):
        course = create_test_course(title="ADM Course Add", sub_title="s", description="d", price=0)
        self._auth(self.moderator)
        url = f"/api/admin-panel/courses/{course.slug}/add-author/?user_id={self.teacher.pk}"
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(course.authors.filter(pk=self.teacher.pk).exists())
        mock_inv.assert_called_once_with(course.slug)

    def test_publish_turns_draft_course_into_published(self):
        course = create_test_course(title="Draft ADM", sub_title="s", description="d", price=0)
        self.assertEqual(course.type, Course.DRAFT_STATUS)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(self.moderator)['access_token']}"
        )
        url = f"/api/admin-panel/courses/{course.slug}/publish/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        course.refresh_from_db()
        self.assertEqual(course.type, Course.PUBLISHED_STATUS)
