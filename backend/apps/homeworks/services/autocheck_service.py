from ..models import QuestionAnswer


class AutocheckService:
    def run(self, attempt):
        question_answers = attempt.question_answers.select_related("question")

        for qa in question_answers:
            is_correct = bool(qa.user_answer) and qa.user_answer == qa.question.correct_ans
            new_status = (
                QuestionAnswer.CORRECT_STATUS if is_correct else QuestionAnswer.INCORRECT_STATUS
            )
            QuestionAnswer.objects.filter(pk=qa.pk).update(
                status=new_status,
                is_correct=is_correct,
            )
