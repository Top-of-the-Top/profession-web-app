from rest_framework import serializers
from apps.courses.api.serializers import CourseDTOSerializer
from ..models import Payment, PaymentItem


class PaymentItemSerializer(serializers.ModelSerializer):
    course = CourseDTOSerializer(read_only=True)

    class Meta:
        model = PaymentItem
        fields = ['id', 'course', 'price']


class PaymentSerializer(serializers.ModelSerializer):
    items = PaymentItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            'payment_id',
            'total_sum',
            'status',
            'status_display',
            'mock_payment_url',
            'mock_yookassa_id',
            'created_at',
            'updated_at',
            'paid_at',
            'items',
        ]


class PaymentShortSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            'payment_id',
            'total_sum',
            'status',
            'status_display',
            'created_at',
            'paid_at',
        ]
