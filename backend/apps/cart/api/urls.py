# courses/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('cart/', CartView.as_view()),
    path('cart/add/<slug:slug>/', AddToCartView.as_view()),
    path('cart/remove/<slug:slug>/', CartItemView.as_view()),
]
