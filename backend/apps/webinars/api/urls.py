from django.urls import path
from . import views

app_name = 'webinars'

urlpatterns = [
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/webinar/start/',
        views.WebinarStartView.as_view(),
        name='webinar-start',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/webinar/stop/',
        views.WebinarStopView.as_view(),
        name='webinar-stop',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/webinar/join/',
        views.WebinarJoinView.as_view(),
        name='webinar-join',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/webinar/recorder-join/',
        views.WebinarRecorderJoinView.as_view(),
        name='webinar-recorder-join',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/webinar/recording/start/',
        views.WebinarRecordingStartView.as_view(),
        name='webinar-recording-start',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/webinar/recording/stop/',
        views.WebinarRecordingStopView.as_view(),
        name='webinar-recording-stop',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/recordings/<uuid:recording_id>/pdf/',
        views.RecordingPdfView.as_view(),
        name='recording-pdf',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/recordings/<uuid:recording_id>/',
        views.RecordingDeleteView.as_view(),
        name='recording-delete',
    ),
    path(
        'kinescope/drm-auth/',
        views.KinescopeDRMAuthView.as_view(),
        name='kinescope-drm-auth',
    ),
]