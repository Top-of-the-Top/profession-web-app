from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views

app_name = 'courses'

urlpatterns = [
    path('landing/courses/', views.CourseDTOList.as_view(),
         name='course-list-preview'),
    path('app/my-courses/', views.PurchasedCoursesView.as_view(),
         name='my-courses'),
]

router = SimpleRouter()

router.register(
    r'app/courses',
    views.CourseViewSet,
    basename='courses'
)

router.register(
    r'courses/(?P<course_slug>[^/.]+)/sections',
    views.SectionViewSet,
    basename='course-sections'
)

router.register(
    r'courses/(?P<course_slug>[^/.]+)/sections/(?P<section_slug>[^/.]+)/lessons',
    views.LessonViewSet,
    basename='section-lessons'
)

router.register(
    r'courses/(?P<course_slug>[^/.]+)/sections/(?P<section_slug>[^/.]+)/lessons/(?P<lesson_slug>[^/.]+)/homeworks',
    views.HomeworkViewSet,
    basename='lesson-homeworks'
)

router.register(
    r'courses/(?P<course_slug>[^/.]+)/sections/(?P<section_slug>[^/.]+)/lessons/(?P<lesson_slug>[^/.]+)/homeworks/(?P<homework_slug>[^/.]+)/questions',
    views.QuestionViewSet,
    basename='homework-questions'
)

router.register(
    r'courses/(?P<course_slug>[^/.]+)/sections/(?P<section_slug>[^/.]+)/lessons/(?P<lesson_slug>[^/.]+)/homeworks/(?P<homework_slug>[^/.]+)/tasks',
    views.TaskViewSet,
    basename='homework-tasks'
)

urlpatterns += router.urls
