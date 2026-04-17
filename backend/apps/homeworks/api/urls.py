from django.urls import path

from .views import (
    HomeworkAttemptSubmitView,
    HomeworkAttemptView,
    HomeworkAttemptListView,
    UploadFileAttachmentView
)


app_name = 'homeworks'


urlpatterns = [
    path(
        'homeworks/<slug:homework_slug>/attempt/',
        HomeworkAttemptView.as_view(),
        name='attempt',
    ),
    path(
        'homeworks/<slug:homework_slug>/attempt/submit',
        HomeworkAttemptSubmitView.as_view(),
        name='attempt-submit',
    ),
    path(
        'homeworks/<slug:homework_slug>/attempt/upload_file',
        UploadFileAttachmentView.as_view(), 
        name='attempt-upload'
    ),
]

urlpatterns += [
  path(
    'app/homeworks/attempts/',
    HomeworkAttemptListView.as_view(),
    name='attempts-list',
  ),
]