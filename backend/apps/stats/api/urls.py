from django.urls import path

from apps.stats.api import views

urlpatterns = [
    path(
        "webinars/<uuid:webinar_id>/attendance/heartbeat/",
        views.WebinarHeartbeatView.as_view(),
        name="webinar-heartbeat",
    ),
    path(
        "recordings/<uuid:recording_id>/view/heartbeat/",
        views.RecordingHeartbeatView.as_view(),
        name="recording-heartbeat",
    ),

    path(
        "webinars/",
        views.StatsWebinarsView.as_view(),
        name="stats-webinars",
    ),
    path(
        "students/",
        views.StatsStudentsView.as_view(),
        name="stats-students",
    ),
    path(
        "students/<int:user_id>/courses/<uuid:course_id>/",
        views.StatsStudentCardView.as_view(),
        name="stats-student-card",
    ),
    path(
        "school/courses/",
        views.StatsSchoolCoursesView.as_view(),
        name="stats-school-courses",
    ),
    path(
        "school/teachers/",
        views.StatsSchoolTeachersView.as_view(),
        name="stats-school-teachers",
    ),
]
