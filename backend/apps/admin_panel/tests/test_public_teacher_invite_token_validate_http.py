from rest_framework import status
from rest_framework.test import APIClient

from apps.admin_panel.models import Invitation
from apps.courses.tests.test_models import BaseTestCase


class PublicTeacherInviteTokenValidateHttpTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_validate_returns_invited_email_for_pending_token(self):
        invite = Invitation.objects.create(email="val@test.local", invited_by=None)
        r = self.client.get("/api/v1/admin-panel/invites/validate/", {"token": invite.token})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["email"], "val@test.local")

    def test_validate_returns_404_for_unknown_token(self):
        r = self.client.get("/api/v1/admin-panel/invites/validate/", {"token": "nonexistent"})
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
