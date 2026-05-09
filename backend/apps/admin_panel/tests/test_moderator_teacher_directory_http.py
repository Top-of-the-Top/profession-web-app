from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.tests.test_models import BaseTestCase, create_test_user
from apps.users.api.utils.token_utils import get_tokens_for_user


class ModeratorTeacherDirectoryHttpTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.moderator = create_test_user(email="adm_mod@test.local", role="moderator")
        self.student = create_test_user(email="adm_st@test.local", role="student")

    def _auth(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(user)['access_token']}"
        )

    def test_list_teachers_requires_moderator_role(self):
        self._auth(self.student)
        r = self.client.get("/api/admin-panel/teachers/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_teachers_returns_payload_for_moderator(self):
        create_test_user(email="adm_tc@test.local", role="teacher")
        self._auth(self.moderator)
        r = self.client.get("/api/admin-panel/teachers/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsInstance(r.data, list)
