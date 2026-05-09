from django.test import TestCase

from apps.admin_panel.api.serializers import InvitationCreateSerializer
from apps.admin_panel.models import Invitation
from apps.courses.tests.test_models import create_test_user


class InvitationCreateSerializerTests(TestCase):
    def test_invalid_when_email_already_registered(self):
        create_test_user(email="taken@test.local", role="teacher")
        ser = InvitationCreateSerializer(data={"email": "taken@test.local"})
        self.assertFalse(ser.is_valid())
        self.assertIn("email", ser.errors)

    def test_invalid_when_active_pending_invite_exists_for_same_email(self):
        moderator = create_test_user(email="mod@test.local", role="moderator")
        Invitation.objects.create(email="pending@test.local", invited_by=moderator)

        ser = InvitationCreateSerializer(data={"email": "pending@test.local"})
        self.assertFalse(ser.is_valid())
        self.assertIn("email", ser.errors)
