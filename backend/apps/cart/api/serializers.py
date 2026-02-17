from rest_framework import serializers
from ..models import *
class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'

class CartSerializer(serializers.ModelSerializer):
    courses = CartItemSerializer(many=True, read_only=True)
    class Meta:
        model = Cart
        fields = '__all__'