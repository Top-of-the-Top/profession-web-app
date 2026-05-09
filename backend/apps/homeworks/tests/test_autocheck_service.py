from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.homeworks.models import QuestionAnswer
from apps.homeworks.services.autocheck_service import AutocheckService


class AutocheckServiceTests(SimpleTestCase):
    def test_updates_each_question_answer_from_correctness(self):
        svc = AutocheckService()

        def qa_pair(user_answer, correct):
            q = MagicMock()
            q.correct_ans = correct
            row = MagicMock()
            row.pk = f"pk-{user_answer}-{correct}"
            row.user_answer = user_answer
            row.question = q
            return row

        rows = [
            qa_pair("ok", "ok"),
            qa_pair("", "ok"),
            qa_pair("no", "yes"),
        ]

        attempt = MagicMock()
        attempt.question_answers.select_related.return_value = rows

        qs_after_filter = MagicMock()
        with patch.object(
            QuestionAnswer.objects, "filter", return_value=qs_after_filter
        ) as m_filter:
            svc.run(attempt)

        self.assertEqual(m_filter.call_count, len(rows))
        updates = [c.kwargs for c in qs_after_filter.update.call_args_list]
        self.assertEqual(updates[0]["is_correct"], True)
        self.assertEqual(updates[0]["status"], QuestionAnswer.CORRECT_STATUS)
        self.assertEqual(updates[1]["is_correct"], False)
        self.assertEqual(updates[2]["is_correct"], False)
