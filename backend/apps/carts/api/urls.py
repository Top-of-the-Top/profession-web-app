# courses/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('carts/', CartView.as_view()),
    path('carts/add/<slug:slug>/', AddToCartView.as_view()),
    path('carts/remove/<slug:slug>/', CartItemView.as_view()),
]
