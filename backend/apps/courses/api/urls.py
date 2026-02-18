# courses/urls.py
from django.urls import path
from .views import CourseDTOList, CourseDTOListAuthenticated, CourseDetail

urlpatterns = [
    path('landing/courses/', CourseDTOList.as_view(), name='course-list-preview'),
    path('app/store/', CourseDTOListAuthenticated.as_view(), name='course-list-store'),
    path('app/courses/<slug>/', CourseDetail.as_view(), name='course-detail'),
]
