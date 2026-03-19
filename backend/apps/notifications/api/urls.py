from django.urls import path
from . import views

urlpatterns = [
    path('notifications/sse/', views.sse_notifications),
]
