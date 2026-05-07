from django.core.cache import caches
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...courses.models import Course
from ..models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer


def cart_hot_cache_key(user_id):
    return f"hot:carts:cart:{int(user_id)}"


SCHEMA_401 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Сообщение об ошибке аутентификации.",
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
            "example": "Курс с таким slug не найден в списке курсов.",
        }
    },
}
SCHEMA_400_ERROR = {
    "type": "object",
    "properties": {
        "error": {
            "type": "string",
            "description": "Ошибка бизнес-логики.",
            "example": "Курс уже в корзине",
        }
    },
}


class CartView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CartSerializer

    @extend_schema(
        summary="Получить корзину пользователя",
        description=(
            "Возвращает корзину текущего пользователя со списком добавленных курсов. "
            "Требуется заголовок Authorization: Bearer <access_token>. "
            "В ответе: cart_id, user, courses (массив объектов курса с course_id, title, sub_title, image_url, price, slug). "
            "При отсутствии или невалидности токена — 401 с полем detail."
        ),
        tags=["Carts"],
        responses={
            200: CartSerializer,
            401: {
                "description": "Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
        },
    )
    def get(self, request):
        hot_cache = caches["hot"]
        cache_key = cart_hot_cache_key(request.user.id)

        cached = hot_cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={"request": request})
        data = serializer.data
        hot_cache.set(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)


class AddToCartView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CartItemSerializer

    @extend_schema(
        summary="Добавить курс в корзину",
        description=(
            "Добавляет курс в корзину текущего пользователя по slug курса (в пути URL). "
            "Требуется Authorization: Bearer <access_token>. "
            "При успехе возвращается созданная позиция корзины (cart_id, course_id, вложенный объект course). "
            "Если курс с таким slug не существует в каталоге — 404 с полем detail. "
            "Если курс уже добавлен в корзину — 400 с полем error: «Курс уже в корзине». "
            "При невалидном токене — 401."
        ),
        tags=["Carts"],
        responses={
            201: CartItemSerializer,
            400: {
                "description": "Тело: { error: 'Курс уже в корзине' }.",
                "schema": SCHEMA_400_ERROR,
            },
            401: {
                "description": "Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
            404: {
                "description": "Тело: { detail: 'Курс с таким slug не найден в списке курсов.' }.",
                "schema": SCHEMA_404,
            },
        },
    )
    def post(self, request, slug):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        course = Course.objects.filter(slug=slug).first()

        if course is None:
            return Response(
                {"detail": "Курс с таким slug не найден в списке курсов."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if CartItem.objects.filter(cart_id=cart.cart_id, course_id=course.course_id).exists():
            return Response(
                {"error": "Курс уже в корзине"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_item = CartItem.objects.create(
            cart_id=cart.cart_id,
            course_id=course.course_id,
        )

        caches["hot"].delete(cart_hot_cache_key(request.user.id))
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CartItemView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Удалить курс из корзины",
        description=(
            "Удаляет курс из корзины текущего пользователя по slug (в пути URL). "
            "Требуется Authorization: Bearer <access_token>. "
            "При успехе возвращается 204 без тела. "
            "404 возвращается в двух случаях: курс с таким slug не найден в каталоге (detail: «Курс с таким slug не найден в списке курсов.») или курс не в корзине (detail: «Курс с таким slug не найден в корзине.»). "
            "При невалидном токене — 401."
        ),
        tags=["Carts"],
        responses={
            204: {"description": "Курс удалён из корзины, тело ответа пустое."},
            401: {
                "description": "Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
            404: {
                "description": "Тело: { detail }. «Курс с таким slug не найден в списке курсов.» или «Курс с таким slug не найден в корзине.»",
                "schema": SCHEMA_404,
            },
        },
    )
    def delete(self, request, slug):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        course = Course.objects.filter(slug=slug).first()
        if course is None:
            return Response(
                {"detail": "Курс с таким slug не найден в списке курсов."},
                status=status.HTTP_404_NOT_FOUND,
            )
        cart_item = CartItem.objects.filter(
            cart_id=cart,
            course_id=course,
        ).first()
        if cart_item is None:
            return Response(
                {"detail": "Курс с таким slug не найден в корзине."},
                status=status.HTTP_404_NOT_FOUND,
            )
        cart_item.delete()
        caches["hot"].delete(cart_hot_cache_key(request.user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)
