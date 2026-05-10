from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import CourseEnrollment
from apps.courses.tests.test_models import create_test_course, create_test_user
from apps.notifications.dispatcher import dispatcher
from apps.notifications.events import (
    ApplicationStatusChangedEvent,
    AuthorActionEvent,
    CourseUpdatedEvent,
    HomeworkReviewedEvent,
    NewHomeworkEvent,
)
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.users.api.utils.token_utils import get_tokens_for_user


class NotificationModelTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="nmod_st@test.local", role="student")
        self.course = create_test_course(title="Model Course")

    def test_notification_str(self):
        n = Notification.objects.create(
            title="Hello",
            message="world",
            notification_type=Notification.PERSONAL,
            user=self.student,
        )
        self.assertEqual(str(n), "Hello")

    def test_personal_notification_visible_to_user(self):
        Notification.objects.create(
            title="Personal",
            message="msg",
            notification_type=Notification.PERSONAL,
            user=self.student,
        )
        qs = Notification.objects.filter(user=self.student)
        self.assertEqual(qs.count(), 1)

    def test_system_notification_has_no_user(self):
        n = Notification.objects.create(
            title="System",
            message="sys",
            notification_type=Notification.SYSTEM,
        )
        self.assertIsNone(n.user)
        self.assertIsNone(n.course)

    def test_read_by_m2m(self):
        n = Notification.objects.create(
            title="Read test",
            message="msg",
            notification_type=Notification.PERSONAL,
            user=self.student,
        )
        n.read_by.add(self.student)
        self.assertIn(self.student, n.read_by.all())


class NotificationApiPaginationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.student = create_test_user(email="npag_st@test.local", role="student")
        self._auth()

    def _auth(self):
        tokens = get_tokens_for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def _create_personal(self, count):
        for i in range(count):
            Notification.objects.create(
                title=f"N{i}",
                message="msg",
                notification_type=Notification.PERSONAL,
                user=self.student,
            )

    def test_pagination_has_more_true_when_over_page_size(self):
        self._create_personal(21)
        r = self.client.get("/api/v1/notifications/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["has_more"])
        self.assertEqual(len(r.data["results"]), 20)

    def test_pagination_has_more_false_when_under_page_size(self):
        self._create_personal(5)
        r = self.client.get("/api/v1/notifications/")
        self.assertFalse(r.data["has_more"])
        self.assertEqual(len(r.data["results"]), 5)

    def test_before_id_cursor_filters_results(self):
        self._create_personal(5)
        all_ids = list(
            Notification.objects.filter(user=self.student)
            .order_by("-id")
            .values_list("id", flat=True)
        )
        pivot = all_ids[2]
        r = self.client.get(f"/api/v1/notifications/?before_id={pivot}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        returned_ids = [row["id"] for row in r.data["results"]]
        self.assertTrue(all(i < pivot for i in returned_ids))

    def test_before_id_invalid_value_ignored(self):
        self._create_personal(3)
        r = self.client.get("/api/v1/notifications/?before_id=notanumber")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 3)

    def test_requires_auth(self):
        self.client.credentials()
        r = self.client.get("/api/v1/notifications/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationTypeFiltersTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.student = create_test_user(email="ntype_st@test.local", role="student")
        self.other = create_test_user(email="ntype_other@test.local", role="student")
        self.course = create_test_course(title="Type Filter Course")
        payment = Payment.objects.create(user=self.student, total_sum=100, status="success")
        CourseEnrollment.objects.create(
            user=self.student,
            course=self.course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )
        tokens = get_tokens_for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_system_notification_visible_to_all_users(self):
        n = Notification.objects.create(
            title="Sys",
            message="global",
            notification_type=Notification.SYSTEM,
        )
        r = self.client.get("/api/v1/notifications/")
        ids = [row["id"] for row in r.data["results"]]
        self.assertIn(n.id, ids)

    def test_course_notification_visible_to_enrolled_student(self):
        n = Notification.objects.create(
            title="Course",
            message="msg",
            course=self.course,
            notification_type=Notification.COURSE,
        )
        r = self.client.get("/api/v1/notifications/")
        ids = [row["id"] for row in r.data["results"]]
        self.assertIn(n.id, ids)

    def test_personal_notification_not_visible_to_other_user(self):
        n = Notification.objects.create(
            title="Private",
            message="only for student",
            notification_type=Notification.PERSONAL,
            user=self.other,
        )
        r = self.client.get("/api/v1/notifications/")
        ids = [row["id"] for row in r.data["results"]]
        self.assertNotIn(n.id, ids)

    def test_mark_all_read_idempotent(self):
        Notification.objects.create(
            title="Read twice",
            message="msg",
            notification_type=Notification.PERSONAL,
            user=self.student,
        )
        self.client.post("/api/v1/notifications/read-all/")
        r2 = self.client.post("/api/v1/notifications/read-all/")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.data["marked"], 0)


class DispatcherExtendedTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="disp_st@test.local", role="student")
        self.course = create_test_course(title="Dispatcher Course")

    @patch("apps.notifications.dispatcher.send_personal_notification.delay")
    def test_author_action_event_dispatches_personal(self, mock_send):
        event = AuthorActionEvent(user_id=self.student.pk, object_repr="Урок 1", action="создан")
        dispatcher.dispatch(event)
        mock_send.assert_called_once()
        args = mock_send.call_args.args
        self.assertEqual(args[0], self.student.pk)

    @patch("apps.notifications.dispatcher.send_course_notification.delay")
    def test_course_updated_event_dispatches_course_notification(self, mock_send):
        event = CourseUpdatedEvent(
            course_id=self.course.course_id,
            course_title=self.course.title,
        )
        dispatcher.dispatch(event)
        mock_send.assert_called_once_with(
            self.course.course_id,
            f"Обновление курса: {self.course.title}",
            "В материалы курса внесены изменения.",
        )

    @patch("apps.notifications.dispatcher.send_personal_notification.delay")
    def test_homework_reviewed_event_dispatches_personal(self, mock_send):
        attempt_id = uuid4()
        event = HomeworkReviewedEvent(
            user_id=self.student.pk,
            homework_title="ДЗ 1",
            grade=90,
            attempt_id=attempt_id,
            with_email=False,
        )
        dispatcher.dispatch(event)
        mock_send.assert_called_once()

    @patch("apps.notifications.dispatcher.send_personal_notification.delay")
    def test_application_status_approved_dispatches_correct_message(self, mock_send):
        event = ApplicationStatusChangedEvent(
            user_id=self.student.pk,
            course_title="Курс X",
            new_status="approved",
        )
        dispatcher.dispatch(event)
        mock_send.assert_called_once()
        _, title, msg = mock_send.call_args.args
        self.assertIn("одобрена", title.lower() + msg.lower())

    @patch("apps.notifications.dispatcher.send_personal_notification.delay")
    def test_application_status_rejected_dispatches_correct_message(self, mock_send):
        event = ApplicationStatusChangedEvent(
            user_id=self.student.pk,
            course_title="Курс Y",
            new_status="rejected",
        )
        dispatcher.dispatch(event)
        mock_send.assert_called_once()
        _, title, msg = mock_send.call_args.args
        self.assertIn("отклонена", title.lower() + msg.lower())

    def test_dispatcher_raises_for_unknown_event(self):
        from apps.notifications.dispatcher import NotificationDispatcher

        local_dispatcher = NotificationDispatcher()

        class UnknownEvent:
            pass

        with self.assertRaises(NotImplementedError):
            local_dispatcher.dispatch(UnknownEvent())

    @patch("apps.notifications.dispatcher.send_course_notification.delay")
    @patch("apps.notifications.dispatcher.send_mass_course_email.delay")
    def test_course_updated_with_email_sends_email(self, mock_email, mock_notif):
        event = CourseUpdatedEvent(
            course_id=self.course.course_id,
            course_title=self.course.title,
            with_email=True,
        )
        dispatcher.dispatch(event)
        mock_email.assert_called_once()
        mock_notif.assert_called_once()
