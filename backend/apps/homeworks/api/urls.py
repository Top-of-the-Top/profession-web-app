from django.urls import path

from .views import (
    AttemptDetailView,
    AttemptReviewView,
    HomeworkAttemptSubmitView,
    HomeworkAttemptView,
    StudentAttemptsView,
    TaskReviewUpdateView,
)

app_name = "homeworks"

urlpatterns = [
    path(
        "courses/<slug:course_slug>/homeworks/<slug:homework_slug>/attempt/",
        HomeworkAttemptView.as_view(),
        name="attempt",
    ),
    path(
        "courses/<slug:course_slug>/homeworks/<slug:homework_slug>/attempt/submit/",
        HomeworkAttemptSubmitView.as_view(),
        name="attempt-submit",
    ),
    path(
        "courses/<slug:course_slug>/attempts/<uuid:attempt_id>/",
        AttemptDetailView.as_view(),
        name="attempt-detail",
    ),
    path(
        "courses/<slug:course_slug>/attempts/<uuid:attempt_id>/review/",
        AttemptReviewView.as_view(),
        name="attempt-review",
    ),
    path(
        "courses/<slug:course_slug>/attempts/<uuid:attempt_id>/review/<uuid:task_answer_id>/",
        TaskReviewUpdateView.as_view(),
        name="task-review-update",
    ),
    path(
        "my-homeworks/",
        StudentAttemptsView.as_view(),
        name="my-homeworks",
    ),
]
