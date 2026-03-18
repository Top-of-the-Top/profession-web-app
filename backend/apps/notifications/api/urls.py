from django.urls import path
from . import views

urlpatterns = [
    path('notifications/trigger/', views.trigger_notification),
    path('notifications/sse/', views.sse_notifications),
]
