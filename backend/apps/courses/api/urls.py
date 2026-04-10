from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path(
        'landing/courses/',
        views.CourseDTOList.as_view(),
        name='course-list-preview',
    ),
]

urlpatterns += [
    path(
        'app/my-courses/',
        views.PurchasedCoursesView.as_view(),
        name='my-courses',
    ),
]

urlpatterns += [
    path(
        'app/courses/<slug:course_slug>/home/',
        views.CourseHomePageView.as_view(),
        name='course-homepage',
    ),
    path('app/courses/', views.CourseListView.as_view(), name='courses-list'),
    path(
        'app/courses/<slug:slug>/',
        views.CourseDetailView.as_view(),
        name='courses-detail',
    ),
]

urlpatterns += [
    path(
        'courses/<slug:course_slug>/sections/',
        views.SectionCreateView.as_view(),
        name='course-sections-list',
    ),
    path(
        'courses/<slug:course_slug>/sections/<slug:section_slug>/',
        views.SectionDetailView.as_view(),
        name='course-sections-detail',
    ),
    path(
        'courses/<slug:course_slug>/lessons/',
        views.LessonCreateView.as_view(),
        name='course-lessons-list',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/',
        views.LessonDetailView.as_view(),
        name='course-lessons-detail',
    ),
]

urlpatterns += [
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/homeworks/',
        views.HomeworkListCreateView.as_view(),
        name='lesson-homeworks-list',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/homeworks/<slug:homework_slug>/tasks/<uuid:task_id>/',
        views.TaskDetailView.as_view(),
        name='homework-tasks-detail',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/homeworks/<slug:homework_slug>/tasks/',
        views.TaskCreateView.as_view(),
        name='homework-tasks-list',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/homeworks/<slug:homework_slug>/questions/<uuid:question_id>/',
        views.QuestionDetailView.as_view(),
        name='homework-questions-detail',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/homeworks/<slug:homework_slug>/questions/',
        views.QuestionCreateView.as_view(),
        name='homework-questions-list',
    ),
    path(
        'courses/<slug:course_slug>/lessons/<slug:lesson_slug>/homeworks/<slug:homework_slug>/',
        views.HomeworkDetailView.as_view(),
        name='lesson-homeworks-detail',
    ),
]
