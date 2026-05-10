from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path(
        "courses/<slug:course_slug>/applications/",
        views.CourseApplicationListView.as_view(),
        name="application-list",
    ),
    path(
        "courses/<slug:course_slug>/applications/apply/",
        views.CourseApplyView.as_view(),
        name="application-apply",
    ),
    path(
        "courses/<slug:course_slug>/applications/my/",
        views.CourseWithdrawApplicationView.as_view(),
        name="application-my",
    ),
    path(
        "courses/<slug:course_slug>/applications/<uuid:application_id>/approve/",
        views.CourseApplicationApproveView.as_view(),
        name="application-approve",
    ),
    path(
        "courses/<slug:course_slug>/applications/<uuid:application_id>/reject/",
        views.CourseApplicationRejectView.as_view(),
        name="application-reject",
    ),
]
