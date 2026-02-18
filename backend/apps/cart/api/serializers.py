from rest_framework import serializers

from apps.courses.api.serializers import CourseDTOSerializer
from ..models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    """Корзина: возвращает список курсов в виде DTO (course_id, title, sub_title, image_url, price, slug)."""
    courses = CourseDTOSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = '__all__'