import uuid
from datetime import timedelta

from django.utils import timezone

from apps.courses.models import Course, Homework, Lesson, Question, Section, Task
from apps.users.models import User


def create_student():
    return User.objects.create_user(
        email_cipher=f"st_{uuid.uuid4().hex}@t.local", password="p", role=User.ROLE_STUDENT
    )


def create_teacher():
    return User.objects.create_user(
        email_cipher=f"tc_{uuid.uuid4().hex}@t.local", password="p", role=User.ROLE_TEACHER
    )


def create_homework_bundle():
    course = Course.objects.create(title="C", sub_title="s", description="d", price=0)
    section = Section.objects.create(course=course, title="S")
    lesson = Lesson.objects.create(section=section, title="L")
    homework = Homework.objects.create(
        lesson=lesson, title="HW", deadline=timezone.now() + timedelta(days=1)
    )
    question = Question.objects.create(
        homework=homework, text="Q1", correct_ans="yes", answer_options=["yes", "no"], max_points=4
    )
    task = Task.objects.create(homework=homework, text="Open task", max_points=6)
    return (homework, question, task)
