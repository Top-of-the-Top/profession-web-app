from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.admin_panel.models import Invitation
from apps.courses.models import Course
from apps.courses.tests.test_models import BaseTestCase, create_test_course, create_test_user
from apps.users.api.utils.token_utils import get_tokens_for_user


class CourseRemoveAuthorHttpTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.moderator = create_test_user(email="rm_mod@test.local", role="moderator")
        self.teacher = create_test_user(email="rm_tc@test.local", role="teacher")
        self.student = create_test_user(email="rm_st@test.local", role="student")
        self.course = create_test_course(title="Remove Author Course")

    def _auth(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(user)['access_token']}"
        )

    def _url(self, slug=None):
        slug = slug or self.course.slug
        return f"/api/v1/admin-panel/courses/{slug}/remove-author/"

    def test_remove_author_requires_auth(self):
        r = self.client.post(self._url())
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_remove_author_requires_moderator_role(self):
        self._auth(self.student)
        r = self.client.post(self._url())
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_author_requires_user_id_param(self):
        self._auth(self.moderator)
        r = self.client.post(self._url())
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "USER_ID_REQUIRED")

    def test_remove_author_user_not_on_course_returns_400(self):
        self._auth(self.moderator)
        r = self.client.post(f"{self._url()}?user_id={self.teacher.pk}")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "AUTHOR_NOT_ON_COURSE")

    @patch("apps.admin_panel.api.views.invalidate_on_course_model_change")
    def test_remove_author_success(self, mock_inv):
        self.course.authors.add(self.teacher)
        self._auth(self.moderator)
        r = self.client.post(f"{self._url()}?user_id={self.teacher.pk}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(self.course.authors.filter(pk=self.teacher.pk).exists())
        mock_inv.assert_called_once_with(self.course.slug)

    @patch("apps.admin_panel.api.views.invalidate_on_course_model_change")
    def test_remove_author_returns_remaining_authors(self, _mock_inv):
        teacher2 = create_test_user(email="rm_tc2@test.local", role="teacher")
        self.course.authors.add(self.teacher, teacher2)
        self._auth(self.moderator)
        r = self.client.post(f"{self._url()}?user_id={self.teacher.pk}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids_in_response = [a["id"] for a in r.data]
        self.assertNotIn(self.teacher.pk, ids_in_response)
        self.assertIn(teacher2.pk, ids_in_response)

    def test_remove_author_course_not_found_returns_404(self):
        self._auth(self.moderator)
        r = self.client.post(
            f"/api/v1/admin-panel/courses/nonexistent-slug/remove-author/?user_id={self.teacher.pk}"
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_author_user_not_teacher_returns_400(self):
        self._auth(self.moderator)
        url = (
            f"/api/v1/admin-panel/courses/{self.course.slug}/add-author/?user_id={self.student.pk}"
        )
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "USER_NOT_TEACHER")

    @patch("apps.admin_panel.api.views.invalidate_on_course_model_change")
    def test_add_author_already_on_course_returns_400(self, _mock_inv):
        self.course.authors.add(self.teacher)
        self._auth(self.moderator)
        url = (
            f"/api/v1/admin-panel/courses/{self.course.slug}/add-author/?user_id={self.teacher.pk}"
        )
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "AUTHOR_ALREADY_ON_COURSE")


class CourseUnpublishHttpTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.moderator = create_test_user(email="unp_mod@test.local", role="moderator")
        self.student = create_test_user(email="unp_st@test.local", role="student")
        self.course = create_test_course(title="Unpublish Course")
        self.course.type = Course.PUBLISHED_STATUS
        self.course.save(update_fields=["type"])

    def _auth(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(user)['access_token']}"
        )

    def test_unpublish_requires_auth(self):
        r = self.client.post(f"/api/v1/admin-panel/courses/{self.course.slug}/unpublish/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unpublish_requires_moderator(self):
        self._auth(self.student)
        r = self.client.post(f"/api/v1/admin-panel/courses/{self.course.slug}/unpublish/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unpublish_published_course_sets_draft(self):
        self._auth(self.moderator)
        r = self.client.post(f"/api/v1/admin-panel/courses/{self.course.slug}/unpublish/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.type, Course.DRAFT_STATUS)
        self.assertEqual(r.data["status"], Course.DRAFT_STATUS)

    def test_unpublish_already_draft_returns_400(self):
        self.course.type = Course.DRAFT_STATUS
        self.course.save(update_fields=["type"])
        self._auth(self.moderator)
        r = self.client.post(f"/api/v1/admin-panel/courses/{self.course.slug}/unpublish/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "COURSE_ALREADY_DRAFT")

    def test_publish_already_published_returns_400(self):
        self._auth(self.moderator)
        r = self.client.post(f"/api/v1/admin-panel/courses/{self.course.slug}/publish/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "COURSE_ALREADY_PUBLISHED")

    def test_unpublish_course_not_found_returns_404(self):
        self._auth(self.moderator)
        r = self.client.post("/api/v1/admin-panel/courses/nope/unpublish/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class InvitationSerializerTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.moderator = create_test_user(email="inv_ser_mod@test.local", role="moderator")

    def _auth(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(self.moderator)['access_token']}"
        )

    @patch("apps.admin_panel.api.views.send_teacher_invite_email", return_value=(True, None))
    def test_invite_duplicate_pending_email_returns_400(self, _mock_email):
        self._auth()
        r1 = self.client.post("/api/v1/admin-panel/invites/send/", {"email": "dup@test.local"})
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        r2 = self.client.post("/api/v1/admin-panel/invites/send/", {"email": "dup@test.local"})
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.admin_panel.api.views.send_teacher_invite_email", return_value=(True, None))
    def test_invite_expired_email_allows_new_invite(self, _mock_email):
        invite = Invitation.objects.create(
            email="expired@test.local",
            invited_by=self.moderator,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(invite.is_expired)
        self._auth()
        r = self.client.post("/api/v1/admin-panel/invites/send/", {"email": "expired@test.local"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    @patch(
        "apps.admin_panel.api.views.send_teacher_invite_email", return_value=(False, "SMTP error")
    )
    def test_invite_email_send_fails_returns_500_and_deletes_invite(self, _mock_email):
        self._auth()
        count_before = Invitation.objects.count()
        r = self.client.post("/api/v1/admin-panel/invites/send/", {"email": "failsend@test.local"})
        self.assertEqual(r.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(r.data["code"], "INVITATION_SEND_FAILED")
        self.assertEqual(Invitation.objects.count(), count_before)
