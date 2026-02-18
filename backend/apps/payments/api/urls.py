from django.urls import path
from .views import (
    CartPayView,
    PaymentListView,
    PaymentDetailView,
)

urlpatterns = [
    path('cart/pay/', CartPayView.as_view(), name='cart-pay'),
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('payments/<int:payment_id>/', PaymentDetailView.as_view(), name='payment-detail'),
]
