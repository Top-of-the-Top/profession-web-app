from django.urls import path
from rest_framework.routers import SimpleRouter
from . import views

app_name = 'courses'

urlpatterns = [
    path('landing/courses/', views.CourseDTOList.as_view(),
         name='course-list-preview'),
    path('app/store/', views.CourseDTOListAuthenticated.as_view(),
         name='course-list-store'),
    path('app/courses/<slug:slug>/', views.CourseDetail.as_view(),
         name='course-detail'),
    path('app/my-courses/', views.PurchasedCoursesView.as_view(),
         name='my-courses'),
]

router = SimpleRouter()
router.register(r'courses/(?P<course_slug>[^/.]+)/lessons', 
                views.LessonViewSet, 
                basename='course-lessons')

router.register(r'courses/(?P<course_slug>[^/.]+)/lessons/(?P<lesson_slug>[^/.]+)/homeworks', 
                views.HomeworkViewSet, 
                basename='lesson-homeworks')

router.register(r'courses/(?P<course_slug>[^/.]+)/lessons/(?P<lesson_slug>[^/.]+)/homeworks/(?P<homework_slug>[^/.]+)/questions', 
                views.QuestionViewSet, 
                basename='homework-questions')

router.register(r'courses/(?P<course_slug>[^/.]+)/lessons/(?P<lesson_slug>[^/.]+)/homeworks/(?P<homework_slug>[^/.]+)/tasks', 
                views.TaskViewSet, 
                basename='homework-tasks')

urlpatterns += router.urls
