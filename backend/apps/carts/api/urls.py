from django.urls import path

from . import views

urlpatterns = [
    path("carts/", views.CartView.as_view(), name="carts"),
    path("carts/add/<slug:slug>/", views.AddToCartView.as_view(), name="carts-add"),
    path("carts/remove/<slug:slug>/", views.CartItemView.as_view(), name="carts-remove"),
]
