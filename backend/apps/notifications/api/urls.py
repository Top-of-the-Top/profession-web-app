from django.urls import path
from . import views

urlpatterns = [
    path('notifications/sse/', views.sse_notifications),
    path('notifications/', views.get_notifications_for_user),
    path('notifications/read-all/', views.mark_all_read),
]
