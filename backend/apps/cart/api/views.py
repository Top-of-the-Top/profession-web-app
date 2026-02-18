from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from ...courses.models import Course
from ..models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer

SCHEMA_401 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Сообщение об ошибке аутентификации (например: учётные данные не переданы или токен недействителен).",
            "example": "Authentication credentials were not provided.",
        }
    },
}
SCHEMA_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Ресурс не найден.",
            "example": "Not found.",
        }
    },
}
SCHEMA_400_ERROR = {
    "type": "object",
    "properties": {
        "error": {
            "type": "string",
            "description": "Описание ошибки валидации или бизнес-логики.",
            "example": "Курс уже в корзине",
        }
    },
}


class CartView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CartSerializer

    @extend_schema(
        summary="Получить корзину пользователя",
        description="Возвращает корзину с перечнем курсов",
        responses={
            200: CartSerializer,
            401: {
                "description": "Не авторизован. Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
        },
    )
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddToCartView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CartItemSerializer

    @extend_schema(
        summary="Добавить курс в корзину",
        description="Добавляет курс по slug в корзину пользователя",
        responses={
            201: CartItemSerializer,
            400: {
                "description": "Курс уже в корзине.",
                "schema": SCHEMA_400_ERROR,
            },
            401: {
                "description": "Не авторизован. Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
            404: {
                "description": "Курс с таким slug не найден в списке курсов.",
                "schema": SCHEMA_404,
            },
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
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Удалить курс из корзины",
        description="Удаляет курс по slug из корзины пользователя",

        responses={
            204: None,
            401: {
                "description": "Не авторизован. Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
            404: {
                "description": "Курс с таким slug не найден в корзине.",
                "schema": SCHEMA_404,
            },
        },
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
