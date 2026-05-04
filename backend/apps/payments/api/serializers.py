from rest_framework import serializers
from apps.courses.models import Course
from ..models import Payment, PaymentItem


class PaymentCourseSerializer(serializers.ModelSerializer):
    """Минимальное представление курса для платежа — без asset-запросов."""

    class Meta:
        model = Course
        fields = ['course_id', 'title', 'sub_title', 'price', 'slug']


class PaymentItemSerializer(serializers.ModelSerializer):
    course = PaymentCourseSerializer(read_only=True)

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
