from django.urls import path

from .views import (
    CourseAddAuthorView,
    CoursePublishView,
    CourseRemoveAuthorView,
    CourseUnpublishView,
    InvitationListView,
    InviteTeacherview,
    InviteValidateView,
    RegisterByInviteView,
    TeacherListView,
)

app_name = "admin_panel"

urlpatterns = [
    path("admin-panel/teachers/", TeacherListView.as_view(), name="teacher-list"),
    path(
        "admin-panel/courses/<slug:course_slug>/add-author/",
        CourseAddAuthorView.as_view(),
        name="course-add-author",
    ),
    path(
        "admin-panel/courses/<slug:course_slug>/remove-author/",
        CourseRemoveAuthorView.as_view(),
        name="course-remove-author",
    ),
    path(
        "admin-panel/courses/<slug:course_slug>/publish/",
        CoursePublishView.as_view(),
        name="course-publish",
    ),
    path(
        "admin-panel/courses/<slug:course_slug>/unpublish/",
        CourseUnpublishView.as_view(),
        name="course-unpublish",
    ),
    path("admin-panel/invites/", InvitationListView.as_view(), name="invite-list"),
    path("admin-panel/invites/send/", InviteTeacherview.as_view(), name="invite-send"),
    path("admin-panel/invites/validate/", InviteValidateView.as_view(), name="invite-validate"),
    path("admin-panel/invites/register/", RegisterByInviteView.as_view(), name="invite-register"),
]
