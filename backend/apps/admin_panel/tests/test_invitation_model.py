import uuid
from datetime import datetime, timedelta
from datetime import timezone as dt_tz
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.admin_panel.models import Invitation


class InvitationPropertiesTests(SimpleTestCase):
    def _invite(self, *, expires_at, used_at=None):
        return Invitation(
            invitation_id=uuid.uuid4(),
            token="test-token",
            email="invite@test.local",
            expires_at=expires_at,
            used_at=used_at,
            invited_by_id=None,
        )

    @patch("apps.admin_panel.models.timezone.now")
    def test_status_pending_when_not_used_before_deadline(self, mock_now):
        mock_now.return_value = datetime(2026, 1, 1, tzinfo=dt_tz.utc)
        inv = self._invite(expires_at=datetime(2026, 1, 5, tzinfo=dt_tz.utc))
        self.assertFalse(inv.is_used)
        self.assertFalse(inv.is_expired)
        self.assertEqual(inv.status, "pending")

    @patch("apps.admin_panel.models.timezone.now")
    def test_status_expired_when_past_deadline(self, mock_now):
        mock_now.return_value = datetime(2026, 2, 1, tzinfo=dt_tz.utc)
        inv = self._invite(expires_at=datetime(2026, 1, 1, tzinfo=dt_tz.utc))
        self.assertTrue(inv.is_expired)
        self.assertEqual(inv.status, "expired")

    def test_status_used_when_used_at_set(self):
        fixed_now = datetime(2026, 3, 1, tzinfo=dt_tz.utc)
        future_exp = fixed_now + timedelta(days=7)
        inv = self._invite(expires_at=future_exp, used_at=fixed_now)
        self.assertTrue(inv.is_used)
        self.assertEqual(inv.status, "used")
