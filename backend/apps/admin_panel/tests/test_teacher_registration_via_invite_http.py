import uuid

from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.admin_panel.models import Invitation
from apps.courses.tests.test_models import BaseTestCase, create_test_user
from apps.users.api.utils.crypto_utils import decrypt_data, encrypt_data
from apps.users.api.utils.token_utils import get_tokens_for_user
from apps.users.models import User


class TeacherRegistrationViaInviteHttpTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.moderator = create_test_user(
            email=f"e2e_mod_{uuid.uuid4().hex}@test.local", role="moderator"
        )

    def _auth_moderator(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(self.moderator)['access_token']}"
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_moderator_sends_invite_then_user_registers_as_teacher(self):
        invite_email = f"e2e_new_teacher_{uuid.uuid4().hex}@test.local"
        mail.outbox.clear()

        self._auth_moderator()
        send_r = self.client.post(
            "/api/v1/admin-panel/invites/send/",
            {"email": invite_email},
            format="json",
        )
        self.assertEqual(send_r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [invite_email])

        invite = Invitation.objects.get(email=invite_email)
        self.assertIsNone(invite.used_at)

        val_r = self.client.get("/api/v1/admin-panel/invites/validate/", {"token": invite.token})
        self.assertEqual(val_r.status_code, status.HTTP_200_OK)
        self.assertEqual(val_r.data["email"], invite_email)

        self.client.credentials()
        reg_r = self.client.post(
            "/api/v1/admin-panel/invites/register/",
            {
                "token": invite.token,
                "password": "longpassword1",
                "first_name": "Иван",
                "last_name": "Препод",
            },
            format="json",
        )
        self.assertEqual(reg_r.status_code, status.HTTP_201_CREATED)
        self.assertIn("access_token", reg_r.data)

        user = User.objects.get(email_cipher=encrypt_data(invite_email))
        self.assertEqual(user.role, User.ROLE_TEACHER)
        self.assertEqual(decrypt_data(user.email_cipher), invite_email)

        invite.refresh_from_db()
        self.assertIsNotNone(invite.used_at)
