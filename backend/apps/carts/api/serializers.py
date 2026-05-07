from rest_framework import serializers
from apps.courses.api.serializers import CourseDTOSerializer
from ..models import Cart, CartItem


class CartCourseSerializer(CourseDTOSerializer):
    class Meta(CourseDTOSerializer.Meta):
        fields = CourseDTOSerializer.Meta.fields + ['price']


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    courses = CartCourseSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = '__all__'
