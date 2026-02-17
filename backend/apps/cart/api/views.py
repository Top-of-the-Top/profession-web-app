from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from ...courses.models import Course
from ..models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer


class CartView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    @extend_schema(
        summary="Получить корзину пользователя",
        description="Возвращает корзину с перечнем курсов",
        responses={200: CartSerializer},
    )
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartItemSerializer

    @extend_schema(
        summary="Добавить курс в корзину",
        description="Добавляет курс по slug в корзину пользователя",
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                description='slug курса',
                required=True
            )
        ],
        responses={
            201: CartItemSerializer,
            400: {
                "description": "Курс уже в корзине",
                "schema": {"type": "object", "properties": {"error": {"type": "string"}}}
            }
        },
        request=None
    )

    def post(self, request, slug):
        cart, _ = Cart.objects.get_or_create(user=request.user)

        if CartItem.objects.filter(cart=cart, course__slug=slug).exists():
            return Response(
                {'error': 'Курс уже в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = get_object_or_404(Course, slug=slug)
        serializer = self.get_serializer(data={'cart': cart.id, 'course': course.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)



class CartItemView(APIView):
    @extend_schema(
        summary="Удалить курс из корзины",
        description="Удаляет курс по slug из корзины пользователя",
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                description='slug курса',
                required=True
            )
        ],

        responses={204: None},
    )

    def delete(self, request, slug):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item = get_object_or_404(
            CartItem,
            cart=cart,
            course__slug=slug
        )
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
