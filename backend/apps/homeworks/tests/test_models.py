from datetime import timedelta

from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.test import TestCase
from django.utils import timezone

from apps.courses.models import Homework, Question, Task
from apps.courses.tests.test_models import (
    BaseTestCase,
    create_test_course,
    create_test_homework,
    create_test_lesson,
    create_test_section,
    create_test_user,
)
from apps.homeworks.models import Attempt, EstimatedMixin, QuestionAnswer, TaskAnswer, TaskReview


def make_question(homework, correct_ans="correct", **kwargs):
    defaults = {
        "homework": homework,
        "text": "Q?",
        "correct_ans": correct_ans,
        "answer_options": ["correct", "wrong"],
    }
    defaults.update(kwargs)
    return Question.objects.create(**defaults)


def make_task(homework, **kwargs):
    defaults = {"homework": homework, "text": "Do something"}
    defaults.update(kwargs)
    return Task.objects.create(**defaults)


def make_attempt(homework, user=None, **kwargs):
    if user is None:
        user = create_test_user(email="hw_model_user@test.local", role="student")
    defaults = {"homework": homework, "user": user}
    defaults.update(kwargs)
    return Attempt.objects.create(**defaults)


class AttemptModelTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.student = create_test_user(email="att_st@test.local", role="student")
        self.teacher = create_test_user(email="att_tc@test.local", role="teacher")
        course = create_test_course(title="HW Model Course")
        section = create_test_section(course)
        lesson = create_test_lesson(section)
        self.homework = create_test_homework(lesson)

    def test_attempt_default_status_is_draft(self):
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        self.assertEqual(attempt.status, Attempt.DRAFT_STATUS)

    def test_attempt_str_returns_uuid(self):
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        self.assertEqual(str(attempt), str(attempt.attempt_id))

    def test_attempt_grade_is_null_by_default(self):
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        self.assertIsNone(attempt.grade)

    def test_attempt_reviewed_by_set_null_on_teacher_delete(self):
        attempt = Attempt.objects.create(
            homework=self.homework, user=self.student, reviewed_by=self.teacher
        )
        self.teacher.delete()
        attempt.refresh_from_db()
        self.assertIsNone(attempt.reviewed_by)

    def test_attempt_cascade_deleted_with_homework(self):
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        aid = attempt.attempt_id
        self.homework.delete()
        self.assertFalse(Attempt.objects.filter(attempt_id=aid).exists())

    def test_attempt_cascade_deleted_with_user(self):
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        aid = attempt.attempt_id
        self.student.delete()
        self.assertFalse(Attempt.objects.filter(attempt_id=aid).exists())

    def test_attempt_unique_per_user_and_homework(self):
        Attempt.objects.create(homework=self.homework, user=self.student)
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                Attempt.objects.create(homework=self.homework, user=self.student)

    def test_attempt_ordering_by_created_at(self):
        student2 = create_test_user(email="att_st2@test.local", role="student")
        a1 = Attempt.objects.create(homework=self.homework, user=self.student)
        a2 = Attempt.objects.create(homework=self.homework, user=student2)
        attempts = list(Attempt.objects.all())
        self.assertEqual(attempts[0], a1)
        self.assertEqual(attempts[1], a2)

    def test_attempt_status_choices(self):
        statuses = [s[0] for s in Attempt.STATUS_CHOICES]
        self.assertIn(Attempt.DRAFT_STATUS, statuses)
        self.assertIn(Attempt.SUBMITTED_STATUS, statuses)
        self.assertIn(Attempt.REVIEWED_STATUS, statuses)


class QuestionAnswerModelTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.student = create_test_user(email="qa_st@test.local", role="student")
        course = create_test_course(title="QA Course")
        section = create_test_section(course)
        lesson = create_test_lesson(section)
        self.homework = create_test_homework(lesson)
        self.question = make_question(self.homework, correct_ans="42")
        self.attempt = Attempt.objects.create(homework=self.homework, user=self.student)

    def test_question_answer_default_is_not_correct(self):
        qa = QuestionAnswer.objects.create(
            question=self.question, attempt=self.attempt, user_answer="42"
        )
        self.assertFalse(qa.is_correct)

    def test_question_answer_str_returns_uuid(self):
        qa = QuestionAnswer.objects.create(question=self.question, attempt=self.attempt)
        self.assertEqual(str(qa), str(qa.answer_id))

    def test_question_answer_status_choices(self):
        statuses = [s[0] for s in QuestionAnswer.STATUS_CHOICES]
        self.assertIn(QuestionAnswer.CORRECT_STATUS, statuses)
        self.assertIn(QuestionAnswer.INCORRECT_STATUS, statuses)
        self.assertIn(QuestionAnswer.PARTIAL_STATUS, statuses)

    def test_question_answer_unique_per_attempt_and_question(self):
        QuestionAnswer.objects.create(question=self.question, attempt=self.attempt)
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                QuestionAnswer.objects.create(question=self.question, attempt=self.attempt)

    def test_question_answer_cascade_deleted_with_attempt(self):
        qa = QuestionAnswer.objects.create(question=self.question, attempt=self.attempt)
        qid = qa.answer_id
        self.attempt.delete()
        self.assertFalse(QuestionAnswer.objects.filter(answer_id=qid).exists())


class TaskAnswerModelTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.student = create_test_user(email="ta_st@test.local", role="student")
        course = create_test_course(title="TA Course")
        section = create_test_section(course)
        lesson = create_test_lesson(section)
        self.homework = create_test_homework(lesson)
        self.task = make_task(self.homework)
        self.attempt = Attempt.objects.create(homework=self.homework, user=self.student)

    def test_task_answer_str_returns_uuid(self):
        ta = TaskAnswer.objects.create(task=self.task, attempt=self.attempt)
        self.assertEqual(str(ta), str(ta.answer_id))

    def test_task_answer_default_user_answer_empty(self):
        ta = TaskAnswer.objects.create(task=self.task, attempt=self.attempt)
        self.assertEqual(ta.user_answer, "")

    def test_task_answer_unique_per_attempt_and_task(self):
        TaskAnswer.objects.create(task=self.task, attempt=self.attempt)
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                TaskAnswer.objects.create(task=self.task, attempt=self.attempt)

    def test_task_answer_cascade_deleted_with_attempt(self):
        ta = TaskAnswer.objects.create(task=self.task, attempt=self.attempt)
        tid = ta.answer_id
        self.attempt.delete()
        self.assertFalse(TaskAnswer.objects.filter(answer_id=tid).exists())


class TaskReviewModelTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.student = create_test_user(email="tr_st@test.local", role="student")
        self.teacher = create_test_user(email="tr_tc@test.local", role="teacher")
        course = create_test_course(title="TR Course")
        section = create_test_section(course)
        lesson = create_test_lesson(section)
        self.homework = create_test_homework(lesson)
        self.task = make_task(self.homework)
        self.attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        self.task_answer = TaskAnswer.objects.create(task=self.task, attempt=self.attempt)

    def test_task_review_default_points_zero(self):
        review = TaskReview.objects.create(answer=self.task_answer, reviewer=self.teacher)
        self.assertEqual(review.points, 0)

    def test_task_review_default_comment_null(self):
        review = TaskReview.objects.create(answer=self.task_answer, reviewer=self.teacher)
        self.assertIsNone(review.comment)

    def test_task_review_reviewer_set_null_on_delete(self):
        review = TaskReview.objects.create(answer=self.task_answer, reviewer=self.teacher)
        self.teacher.delete()
        review.refresh_from_db()
        self.assertIsNone(review.reviewer)

    def test_task_review_str_returns_uuid(self):
        review = TaskReview.objects.create(answer=self.task_answer)
        self.assertIn(str(review.task_review_id), str(review.task_review_id))

    def test_task_review_is_one_to_one_with_task_answer(self):
        TaskReview.objects.create(answer=self.task_answer)
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                TaskReview.objects.create(answer=self.task_answer)


class AutocheckServiceIntegrationTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.student = create_test_user(email="autocheck_st@test.local", role="student")
        course = create_test_course(title="Autocheck Course")
        section = create_test_section(course)
        lesson = create_test_lesson(section)
        self.homework = create_test_homework(lesson)

    def test_autocheck_marks_correct_answer(self):
        from apps.homeworks.services.autocheck_service import AutocheckService

        q = make_question(self.homework, correct_ans="42")
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        qa = QuestionAnswer.objects.create(question=q, attempt=attempt, user_answer="42")
        AutocheckService().run(attempt)
        qa.refresh_from_db()
        self.assertTrue(qa.is_correct)
        self.assertEqual(qa.status, QuestionAnswer.CORRECT_STATUS)

    def test_autocheck_marks_wrong_answer(self):
        from apps.homeworks.services.autocheck_service import AutocheckService

        q = make_question(self.homework, correct_ans="42")
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        qa = QuestionAnswer.objects.create(question=q, attempt=attempt, user_answer="99")
        AutocheckService().run(attempt)
        qa.refresh_from_db()
        self.assertFalse(qa.is_correct)
        self.assertEqual(qa.status, QuestionAnswer.INCORRECT_STATUS)

    def test_autocheck_marks_empty_answer_as_incorrect(self):
        from apps.homeworks.services.autocheck_service import AutocheckService

        q = make_question(self.homework, correct_ans="42")
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        qa = QuestionAnswer.objects.create(question=q, attempt=attempt, user_answer="")
        AutocheckService().run(attempt)
        qa.refresh_from_db()
        self.assertFalse(qa.is_correct)
        self.assertEqual(qa.status, QuestionAnswer.INCORRECT_STATUS)

    def test_autocheck_handles_multiple_questions(self):
        from apps.homeworks.services.autocheck_service import AutocheckService

        q1 = make_question(self.homework, correct_ans="yes", text="Q1?")
        q2 = make_question(self.homework, correct_ans="no", text="Q2?")
        attempt = Attempt.objects.create(homework=self.homework, user=self.student)
        qa1 = QuestionAnswer.objects.create(question=q1, attempt=attempt, user_answer="yes")
        qa2 = QuestionAnswer.objects.create(question=q2, attempt=attempt, user_answer="wrong")
        AutocheckService().run(attempt)
        qa1.refresh_from_db()
        qa2.refresh_from_db()
        self.assertTrue(qa1.is_correct)
        self.assertFalse(qa2.is_correct)
