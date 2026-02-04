# courses/urls.py
from django.urls import path
from .views import CourseList

urlpatterns = [
    path('landing/courses/', CourseList.as_view(), name='course-list'),
]
