from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from apps.core.api.permissions import require_moderator
from apps.core.processors.error_processor import process_error_response
from apps.courses.tests.test_models import create_test_user


class FakeError(Exception):
    code = "FAKE_ERROR"
    message = "Fake error message"
    status = status.HTTP_400_BAD_REQUEST
    details = {"key": "value"}


class RequireModeratorDecoratorTests(SimpleTestCase):

    def _make_view(self):
        @require_moderator
        def view(request):
            return MagicMock(status_code=200)

        return view

    def test_unauthenticated_request_returns_401(self):
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = False
        view = self._make_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_moderator_returns_403(self):
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.is_moderator.return_value = False
        view = self._make_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_calls_view(self):
        sentinel = object()
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.is_moderator.return_value = True

        @require_moderator
        def view(request):
            return sentinel

        result = view(request)
        self.assertIs(result, sentinel)

    def test_no_request_returns_401(self):
        view = self._make_view()
        response = view()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_request_as_second_arg(self):
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = False

        @require_moderator
        def view(self_arg, request):
            return MagicMock(status_code=200)

        response = view(None, request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProcessErrorResponseTests(SimpleTestCase):

    def test_returns_correct_status_code(self):
        exc = FakeError()
        response = process_error_response(exc)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_response_contains_code_and_message(self):
        exc = FakeError()
        response = process_error_response(exc)
        self.assertEqual(response.data["code"], "FAKE_ERROR")
        self.assertEqual(response.data["message"], "Fake error message")

    def test_response_contains_details(self):
        exc = FakeError()
        response = process_error_response(exc)
        self.assertEqual(response.data["details"], {"key": "value"})

    def test_response_status_field_is_error(self):
        exc = FakeError()
        response = process_error_response(exc)
        self.assertEqual(response.data["status"], "error")

    def test_none_details_becomes_empty_dict(self):
        exc = FakeError()
        exc.details = None
        response = process_error_response(exc)
        self.assertEqual(response.data["details"], {})


class RequireModeratorIntegrationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.moderator = create_test_user(email="core_mod@test.local", role="moderator")
        self.teacher = create_test_user(email="core_tc@test.local", role="teacher")

    def _auth(self, user):
        from apps.users.api.utils.token_utils import get_tokens_for_user

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(user)['access_token']}"
        )

    def test_moderator_can_access_teacher_list(self):
        self._auth(self.moderator)
        r = self.client.get("/api/v1/admin-panel/teachers/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_teacher_cannot_access_teacher_list(self):
        self._auth(self.teacher)
        r = self.client.get("/api/v1/admin-panel/teachers/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access_teacher_list(self):
        r = self.client.get("/api/v1/admin-panel/teachers/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
