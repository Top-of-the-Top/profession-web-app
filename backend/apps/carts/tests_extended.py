from unittest.mock import patch

from django.core.cache import caches
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.carts.api.cache_utils import cart_hot_cache_key
from apps.carts.models import Cart, CartItem
from apps.courses.api.utils.cache_utils import purchased_courses_cache_key
from apps.courses.models import Course
from apps.courses.tests.test_models import create_test_course, create_test_user, publish_course_tree
from apps.users.api.utils.token_utils import get_tokens_for_user


def create_special_course(**kwargs):
    defaults = {
        "title": "Special Course",
        "sub_title": "Special subtitle for the course",
        "description": "Special description for the course",
        "price": 0,
        "is_special": True,
    }
    defaults.update(kwargs)
    return Course.objects.create(**defaults)


class CartSpecialCourseTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.student = create_test_user(email="cart_spec_st@test.local", role="student")
        caches["hot"].delete(cart_hot_cache_key(self.student.id))
        caches["default"].delete(purchased_courses_cache_key(self.student.id))
        self._auth()

    def _auth(self):
        tokens = get_tokens_for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_add_special_course_to_cart_returns_404(self):
        course = create_special_course(title="Special Hidden")
        course.type = Course.PUBLISHED_STATUS
        course.save(update_fields=["type"])
        r = self.client.post(f"/api/v1/carts/add/{course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_unpublished_course_returns_404(self):
        course = create_test_course(title="Draft Course")
        r = self.client.post(f"/api/v1/carts/add/{course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_nonexistent_course_returns_404(self):
        r = self.client.post("/api/v1/carts/add/no-such-course/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_same_course_twice_returns_400(self):
        course = create_test_course(title="Dup Course")
        publish_course_tree(course)
        self.client.post(f"/api/v1/carts/add/{course.slug}/")
        r2 = self.client.post(f"/api/v1/carts/add/{course.slug}/")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r2.data["code"], "COURSE_ALREADY_IN_CART")

    def test_add_to_cart_invalidates_hot_cache(self):
        course = create_test_course(title="Cache Inval Course")
        publish_course_tree(course)
        key = cart_hot_cache_key(self.student.id)
        caches["hot"].set(key, {"items": []})
        self.client.post(f"/api/v1/carts/add/{course.slug}/")
        self.assertIsNone(caches["hot"].get(key))


class CartCacheTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.student = create_test_user(email="cart_cache_st@test.local", role="student")
        caches["hot"].delete(cart_hot_cache_key(self.student.id))
        caches["default"].delete(purchased_courses_cache_key(self.student.id))
        tokens = get_tokens_for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_cart_view_stores_result_in_hot_cache(self):
        key = cart_hot_cache_key(self.student.id)
        caches["hot"].delete(key)
        self.client.get("/api/v1/carts/")
        self.assertIsNotNone(caches["hot"].get(key))

    def test_cart_view_returns_cached_data_on_second_call(self):
        key = cart_hot_cache_key(self.student.id)
        caches["hot"].delete(key)
        r1 = self.client.get("/api/v1/carts/")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        r2 = self.client.get("/api/v1/carts/")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r1.data, r2.data)

    def test_cart_delete_invalidates_cache(self):
        course = create_test_course(title="Delete Cache Course")
        publish_course_tree(course)
        add_r = self.client.post(f"/api/v1/carts/add/{course.slug}/")
        self.assertEqual(add_r.status_code, status.HTTP_201_CREATED)
        key = cart_hot_cache_key(self.student.id)
        caches["hot"].set(key, {"old": "data"})
        self.client.delete(f"/api/v1/carts/remove/{course.slug}/")
        self.assertIsNone(caches["hot"].get(key))


class CartItemDeleteTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.student = create_test_user(email="cart_del_st@test.local", role="student")
        caches["hot"].delete(cart_hot_cache_key(self.student.id))
        caches["default"].delete(purchased_courses_cache_key(self.student.id))
        tokens = get_tokens_for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        self.course = create_test_course(title="Delete Item Course")
        publish_course_tree(self.course)
        self.client.post(f"/api/v1/carts/add/{self.course.slug}/")

    def test_delete_item_from_cart_returns_204(self):
        r = self.client.delete(f"/api/v1/carts/remove/{self.course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        cart = Cart.objects.get(user=self.student)
        self.assertFalse(CartItem.objects.filter(cart=cart, course=self.course).exists())

    def test_delete_nonexistent_item_returns_404(self):
        r = self.client.delete("/api/v1/carts/remove/no-such-slug/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_other_users_item_returns_404(self):
        other = create_test_user(email="cart_del_other@test.local", role="student")
        caches["hot"].delete(cart_hot_cache_key(other.id))
        other_tokens = get_tokens_for_user(other)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_tokens['access_token']}")
        r = self.client.delete(f"/api/v1/carts/remove/{self.course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        cart = Cart.objects.get(user=self.student)
        self.assertTrue(CartItem.objects.filter(cart=cart, course=self.course).exists())

    def test_delete_requires_auth(self):
        self.client.credentials()
        r = self.client.delete(f"/api/v1/carts/remove/{self.course.slug}/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.payments.api.views.process_payment_task.apply_async")
    def test_pay_cart_with_special_course_blocked(self, mock_task):
        special = create_special_course()
        special.type = Course.PUBLISHED_STATUS
        special.is_special = False
        special.save()
        cart, _ = Cart.objects.get_or_create(user=self.student)
        CartItem.objects.get_or_create(cart=cart, course=special)
        tokens = get_tokens_for_user(self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        special.is_special = True
        special.save()
        r = self.client.post("/api/v1/carts/pay/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["code"], "SPECIAL_COURSE_IN_CART")
