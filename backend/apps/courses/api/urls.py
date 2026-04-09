from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views

app_name = 'courses'

urlpatterns = [
    path('landing/courses/', views.CourseDTOList.as_view(),
         name='course-list-preview'),
    path('app/my-courses/', views.PurchasedCoursesView.as_view(),
         name='my-courses'),
    path('app/courses/<slug:course_slug>/home/', views.CourseHomePageView.as_view(),
         name='course-homepage'),
]

router = SimpleRouter()

router.register(
    r'app/courses',
    views.CourseViewSet,
    basename='courses'
)

router.register(
    r'courses/(?P<course_slug>[^/.]+)/lessons',
    views.LessonViewSet,
    basename='course-lessons'
)

router.register(
    r'courses/(?P<course_slug>[^/.]+)/lessons/(?P<lesson_slug>[^/.]+)/homeworks',
    views.HomeworkViewSet,
    basename='lesson-homeworks'
)

urlpatterns += router.urls
