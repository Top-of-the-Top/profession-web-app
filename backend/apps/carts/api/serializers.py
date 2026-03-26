from rest_framework import serializers
from apps.courses.api.serializers import CourseDTOSerializer
from ..models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    courses = CourseDTOSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = '__all__'
