from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from apps.carts.models import Cart, CartItem

from types import SimpleNamespace

from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.carts.api.views import (
    CartView, AddToCartView, CartItemView
)


class CartModelUnitTests(SimpleTestCase):

    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.pk = 1
        self.mock_user.username = 'testuser'

        self.mock_cart = MagicMock(spec=Cart)
        self.mock_cart.cart_id = 1
        self.mock_cart.user = self.mock_user

        self.mock_course = MagicMock()
        self.mock_course.course_id = 1
        self.mock_course.pk = 1
        self.mock_course.title = 'Тестовый курс'

    def test_cart_creation_with_mock(self):
        """Тест создания корзины через мок"""
        mock_cart = MagicMock(spec=Cart)
        mock_cart.cart_id = 1
        mock_cart.user = self.mock_user

        self.assertEqual(mock_cart.cart_id, 1)
        self.assertEqual(mock_cart.user, self.mock_user)

    def test_cart_str_method(self):
        """Тест строкового представления корзины"""
        mock_cart = MagicMock(spec=Cart)
        mock_cart.cart_id = 1
        mock_cart.user = self.mock_user
        mock_cart.__str__.return_value = f'Cart #{mock_cart.cart_id} for {mock_cart.user.username}'

        expected = f'Cart #1 for testuser'
        self.assertEqual(str(mock_cart), expected)


class CartItemModelUnitTests(SimpleTestCase):

    def setUp(self):
        self.mock_cart = MagicMock(spec=Cart)
        self.mock_cart.cart_id = 1
        self.mock_cart.pk = 1

        self.mock_course = MagicMock()
        self.mock_course.course_id = 1
        self.mock_course.pk = 1
        self.mock_course.title = 'Тестовый курс'

        self.mock_cart_item = MagicMock(spec=CartItem)
        self.mock_cart_item.cart_id = self.mock_cart
        self.mock_cart_item.course_id = self.mock_course

    def test_cart_item_creation_with_mock(self):
        """Тест создания элемента корзины через мок"""
        mock_item = MagicMock(spec=CartItem)
        mock_item.cart_id = self.mock_cart
        mock_item.course_id = self.mock_course

        self.assertEqual(mock_item.cart_id, self.mock_cart)
        self.assertEqual(mock_item.course_id, self.mock_course)

    def test_cart_item_foreign_keys(self):
        """Тест внешних ключей"""
        mock_item = MagicMock(spec=CartItem)
        mock_item.cart_id = self.mock_cart
        mock_item.course_id = self.mock_course

        self.assertIsNotNone(mock_item.cart_id)
        self.assertIsNotNone(mock_item.course_id)
        self.assertEqual(mock_item.cart_id.cart_id, 1)
        self.assertEqual(mock_item.course_id.course_id, 1)

    def test_cart_item_unique_together(self):
        """Тест уникальности пары cart-course"""

        self.assertTrue(hasattr(CartItem._meta, 'unique_together'))
        self.assertIn(('cart_id', 'course_id'), CartItem._meta.unique_together)


class CartIntegrationUnitTests(SimpleTestCase):

    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.pk = 1

        self.mock_cart = MagicMock(spec=Cart)
        self.mock_cart.cart_id = 1
        self.mock_cart.user = self.mock_user

        self.mock_course1 = MagicMock()
        self.mock_course1.course_id = 1
        self.mock_course1.pk = 1
        self.mock_course1.title = 'Курс 1'

        self.mock_course2 = MagicMock()
        self.mock_course2.course_id = 2
        self.mock_course2.pk = 2
        self.mock_course2.title = 'Курс 2'

    def test_cart_items_relationship(self):
        """Тест связи корзины с элементами"""
        mock_items = MagicMock()
        mock_items.all.return_value = [
            MagicMock(course_id=self.mock_course1),
            MagicMock(course_id=self.mock_course2)
        ]
        self.mock_cart.cartitem_set = mock_items

        items = self.mock_cart.cartitem_set.all()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].course_id.title, 'Курс 1')
        self.assertEqual(items[1].course_id.title, 'Курс 2')

    def test_cart_total_price_calculation(self):
        """Тест расчета общей суммы корзины"""
        # Добавляем цену к курсам
        self.mock_course1.price = 5000
        self.mock_course2.price = 3000

        mock_item1 = MagicMock()
        mock_item1.course_id = self.mock_course1

        mock_item2 = MagicMock()
        mock_item2.course_id = self.mock_course2

        mock_items = MagicMock()
        mock_items.all.return_value = [mock_item1, mock_item2]
        self.mock_cart.cartitem_set = mock_items

        total = sum(
            item.course_id.price for item in self.mock_cart.cartitem_set.all())

        self.assertEqual(total, 8000)

    def test_add_course_to_cart(self):
        """Тест добавления курса в корзину"""
        self.mock_cart.courses.add = MagicMock()

        self.mock_cart.courses.add(self.mock_course1)

        self.mock_cart.courses.add.assert_called_once_with(self.mock_course1)

    def test_remove_course_from_cart(self):
        """Тест удаления курса из корзины"""
        self.mock_cart.courses.remove = MagicMock()

        self.mock_cart.courses.remove(self.mock_course1)

        self.mock_cart.courses.remove.assert_called_once_with(
            self.mock_course1)

    def test_clear_cart(self):
        """Тест очистки корзины"""
        self.mock_cart.courses.clear = MagicMock()

        self.mock_cart.courses.clear()

        self.mock_cart.courses.clear.assert_called_once()

    def test_course_uniqueness_in_cart(self):
        """Тест что курс не может быть добавлен дважды"""
        self.assertIn(('cart_id', 'course_id'), CartItem._meta.unique_together)

        mock_item = MagicMock(spec=CartItem)
        mock_item.cart_id = self.mock_cart
        mock_item.course_id = self.mock_course1

        self.assertEqual(mock_item.cart_id, self.mock_cart)
        self.assertEqual(mock_item.course_id, self.mock_course1)


class CartAuthUnitTests(SimpleTestCase):

    databases = "__all__"

    def setUp(self):
        self.factory = APIRequestFactory()

        # Создаем авторизованного пользователя

        self.auth_user = SimpleNamespace(
            id=1,
            pk=1,
            is_authenticated=True
        )

        # Создаем неавторизованного пользователя
        self.anon_user = SimpleNamespace(
            is_authenticated=False
        )

        # Моки для Cart и Course
        self.mock_cart = MagicMock()
        self.mock_cart.cart_id = 1
        self.mock_cart.user = self.auth_user

        self.mock_course = MagicMock()
        self.mock_course.course_id = 1
        self.mock_course.pk = 1
        self.mock_course.slug = 'test-course'
        self.mock_course.title = 'Тестовый курс'

    # Тесты для CartView (GET /api/cart/)

    def test_cart_view_without_auth(self):
        """Тест что CartView возвращает 401 для неавторизованного"""
        request = self.factory.get('/api/cart/')
        response = CartView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_view_with_auth(self):
        """Тест что CartView работает для авторизованного"""
        request = self.factory.get('/api/cart/')
        force_authenticate(request, user=self.auth_user)

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_get_or_create, \
                patch('apps.carts.api.views.CartSerializer') as mock_serializer:
            mock_get_or_create.return_value = (self.mock_cart, True)
            mock_serializer.return_value.data = {'cart_id': 1, 'items': []}

            response = CartView.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_get_or_create.assert_called_once_with(user=self.auth_user)

    # Тесты для AddToCartView (POST /api/cart/add/<slug>/)

    def test_add_to_cart_view_without_auth(self):
        """Тест что AddToCartView возвращает 401 для неавторизованного"""
        request = self.factory.post('/api/cart/add/test-course/')
        response = AddToCartView.as_view()(request, slug='test-course')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_to_cart_view_with_auth_course_not_found(self):
        """Тест AddToCartView с авторизацией но курс не найден"""
        request = self.factory.post('/api/cart/add/non-existent/')
        force_authenticate(request, user=self.auth_user)

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_cart_get, \
                patch('apps.carts.api.views.Course.objects.filter') as mock_course_filter:
            mock_cart_get.return_value = (self.mock_cart, True)
            mock_course_filter.return_value.first.return_value = None

            response = AddToCartView.as_view()(request, slug='non-existent')

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('detail', response.data)

    def test_add_to_cart_view_with_auth_success(self):
        """Тест успешного добавления курса авторизованным пользователем"""
        request = self.factory.post('/api/cart/add/test-course/')
        force_authenticate(request, user=self.auth_user)

        mock_cart_item = MagicMock()
        mock_cart_item.cart_id = self.mock_cart
        mock_cart_item.course_id = self.mock_course

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_cart_get, \
                patch('apps.carts.api.views.Course.objects.filter') as mock_course_filter, \
                patch('apps.carts.api.views.CartItem.objects.filter') as mock_item_filter, \
                patch('apps.carts.api.views.CartItem.objects.create') as mock_item_create, \
                patch('apps.carts.api.views.CartItemSerializer') as mock_serializer:
            mock_cart_get.return_value = (self.mock_cart, True)
            mock_course_filter.return_value.first.return_value = self.mock_course
            mock_item_filter.return_value.exists.return_value = False
            mock_item_create.return_value = mock_cart_item
            mock_serializer.return_value.data = {
                'cart_id': 1,
                'course': {'title': 'Тестовый курс'}
            }

            response = AddToCartView.as_view()(request, slug='test-course')

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_item_create.assert_called_once_with(
                cart_id=self.mock_cart.cart_id,
                course_id=self.mock_course.course_id
            )

    def test_add_to_cart_view_course_already_in_cart(self):
        """Тест добавления курса который уже в корзине"""
        request = self.factory.post('/api/cart/add/test-course/')
        force_authenticate(request, user=self.auth_user)

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_cart_get, \
                patch('apps.carts.api.views.Course.objects.filter') as mock_course_filter, \
                patch('apps.carts.api.views.CartItem.objects.filter') as mock_item_filter:
            mock_cart_get.return_value = (self.mock_cart, True)
            mock_course_filter.return_value.first.return_value = self.mock_course
            mock_item_filter.return_value.exists.return_value = True

            response = AddToCartView.as_view()(request, slug='test-course')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('error', response.data)
            self.assertEqual(response.data['error'], 'Курс уже в корзине')

    def test_cart_item_view_without_auth(self):
        """Тест что CartItemView возвращает 401 для неавторизованного"""
        request = self.factory.delete('/api/cart/remove/test-course/')
        response = CartItemView.as_view()(request, slug='test-course')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_item_view_with_auth_course_not_found(self):
        """Тест CartItemView с авторизацией но курс не найден в корзине"""
        request = self.factory.delete('/api/cart/remove/test-course/')
        force_authenticate(request, user=self.auth_user)

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_cart_get, \
                patch('apps.carts.api.views.Course.objects.get') as mock_course_get, \
                patch('apps.carts.api.views.CartItem.objects.filter') as mock_item_filter:
            mock_cart_get.return_value = (self.mock_cart, True)
            mock_course_get.return_value = self.mock_course
            mock_item_filter.return_value.first.return_value = None

            response = CartItemView.as_view()(request, slug='test-course')

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('detail', response.data)

    def test_cart_item_view_with_auth_success(self):
        """Тест успешного удаления курса из корзины авторизованным пользователем"""
        request = self.factory.delete('/api/carts/remove/test-course/')
        force_authenticate(request, user=self.auth_user)

        mock_cart_item = MagicMock()
        mock_cart_item.delete = MagicMock()

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_cart_get, \
                patch('apps.carts.api.views.Course.objects.filter') as mock_course_filter, \
                patch('apps.carts.api.views.CartItem.objects.filter') as mock_cartitem_filter:
            mock_cart_get.return_value = (self.mock_cart, True)

            mock_course_filter.return_value.first.return_value = self.mock_course

            mock_cartitem_filter.return_value.first.return_value = mock_cart_item

            response = CartItemView.as_view()(request, 'test-course')

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_cart_item.delete.assert_called_once()


class CartPermissionsUnitTests(SimpleTestCase):
    """Тесты permission_classes для Cart views"""

    def test_cart_view_permission_classes(self):
        """Тест что CartView требует IsAuthenticated"""
        view = CartView()
        permissions = view.get_permissions()

        self.assertEqual(len(permissions), 1)
        self.assertEqual(permissions[0].__class__.__name__, 'IsAuthenticated')

    def test_add_to_cart_view_permission_classes(self):
        """Тест что AddToCartView требует IsAuthenticated"""
        view = AddToCartView()
        permissions = view.get_permissions()

        self.assertEqual(len(permissions), 1)
        self.assertEqual(permissions[0].__class__.__name__, 'IsAuthenticated')

    def test_cart_item_view_permission_classes(self):
        """Тест что CartItemView требует IsAuthenticated"""
        view = CartItemView()
        permissions = view.get_permissions()

        self.assertEqual(len(permissions), 1)
        self.assertEqual(permissions[0].__class__.__name__, 'IsAuthenticated')


class CartViewUnitTests(SimpleTestCase):
   
    def setUp(self):
        self.factory = APIRequestFactory()
        self.auth_user = SimpleNamespace(
            id=1,
            pk=1,
            is_authenticated=True
        )
        self.mock_cart = MagicMock()
        self.mock_cart.cart_id = 1

    def test_cart_view_get_or_create_called(self):
        """Тест что get_or_create вызывается с правильным пользователем"""
        request = self.factory.get('/api/cart/')
        force_authenticate(request, user=self.auth_user)

        mock_hot_cache = MagicMock()
        mock_hot_cache.get.return_value = None

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_get_or_create, \
                patch('apps.carts.api.views.CartSerializer') as mock_serializer, \
                patch('apps.carts.api.views.caches', {'hot': mock_hot_cache}):
            mock_get_or_create.return_value = (self.mock_cart, True)
            mock_serializer.return_value.data = {}

            CartView.as_view()(request)

            mock_get_or_create.assert_called_once_with(user=self.auth_user)

    def test_cart_view_returns_serialized_data(self):
        """Тест что CartView возвращает сериализованные данные"""
        request = self.factory.get('/api/cart/')
        force_authenticate(request, user=self.auth_user)

        expected_data = {
            'cart_id': 1,
            'items': [
                {'course_id': 1, 'title': 'Курс 1'},
                {'course_id': 2, 'title': 'Курс 2'}
            ]
        }

        mock_hot_cache = MagicMock()
        mock_hot_cache.get.return_value = None

        with patch('apps.carts.api.views.Cart.objects.get_or_create') as mock_get_or_create, \
                patch('apps.carts.api.views.CartSerializer') as mock_serializer, \
                patch('apps.carts.api.views.caches', {'hot': mock_hot_cache}):
            mock_get_or_create.return_value = (self.mock_cart, True)
            mock_serializer.return_value.data = expected_data

            response = CartView.as_view()(request)

            self.assertEqual(response.data, expected_data)
