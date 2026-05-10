from django.core.cache import caches
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import ServiceErrorResponseSerializer
from apps.core.processors.error_processor import process_error_response

from ...courses.models import Course
from ..models import Cart, CartItem
from .cache_utils import cart_hot_cache_key
from .errors import CourseAlreadyInCart, CourseNotAvailable, CourseNotInCart
from .serializers import CartItemSerializer, CartSerializer

SCHEMA_401 = {
    "type": "object",
    "properties": {"detail": {"type": "string"}},
}

_PATH_SLUG = OpenApiParameter(
    "slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
)


class CartView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CartSerializer

    @extend_schema(
        summary="Корзина пользователя",
        description="Возвращает корзину текущего пользователя с добавленными курсами.",
        tags=["Carts"],
        responses={
            200: CartSerializer,
            401: {"schema": SCHEMA_401},
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
            "Добавляет опубликованный публичный курс в корзину по его slug. "
            "Специальные (is_special) курсы добавить нельзя."
        ),
        tags=["Carts"],
        parameters=[_PATH_SLUG],
        responses={
            201: CartItemSerializer,
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_401},
            404: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request, slug):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        course = Course.objects.filter(
            slug=slug, is_deleted=False, type=Course.PUBLISHED_STATUS, is_special=False
        ).first()

        if course is None:
            return process_error_response(CourseNotAvailable())

        if CartItem.objects.filter(cart_id=cart.cart_id, course_id=course.course_id).exists():
            return process_error_response(CourseAlreadyInCart())

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
        description="Удаляет курс из корзины текущего пользователя по slug.",
        tags=["Carts"],
        parameters=[_PATH_SLUG],
        responses={
            204: None,
            401: {"schema": SCHEMA_401},
            404: ServiceErrorResponseSerializer,
        },
    )
    def delete(self, request, slug):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        course = Course.objects.filter(slug=slug).first()
        if course is None:
            return process_error_response(CourseNotAvailable())

        cart_item = CartItem.objects.filter(cart_id=cart, course_id=course).first()
        if cart_item is None:
            return process_error_response(CourseNotInCart())

        cart_item.delete()
        caches["hot"].delete(cart_hot_cache_key(request.user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)
