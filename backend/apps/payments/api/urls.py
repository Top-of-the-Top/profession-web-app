from django.urls import path
from .views import (
    CartPayView,
    PaymentListView,
    PaymentDetailView,
    PurchasedCoursesView,
)

urlpatterns = [
    path('cart/pay/', CartPayView.as_view(), name='cart-pay'),
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('payments/purchased/', PurchasedCoursesView.as_view(), name='purchased-courses'),
    path('payments/<int:payment_id>/', PaymentDetailView.as_view(), name='payment-detail'),
]
