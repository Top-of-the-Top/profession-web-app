from django.core.cache import caches
from django.test import TestCase

from apps.courses.api.utils.cache_utils import (
    attempt_detail_cache_key,
    attempt_draft_cache_key,
    attempt_list_by_course_cache_key,
    attempt_list_cache_key,
    cached_detail_response,
    course_detail_cache_key,
    course_list_cache_key,
    enrolled_courses_cache_key,
    homework_detail_cache_key,
    invalidate_attempt_cache,
    invalidate_on_course_model_change,
    invalidate_on_lesson_model_change,
    invalidate_on_section_model_change,
    invalidate_schedule_cache,
    invalidate_user_role_cache,
    landing_courses_cache_key,
    lesson_detail_cache_key,
    lesson_list_cache_key,
    my_schedule_cache_key,
    purchased_courses_cache_key,
    section_detail_cache_key,
    section_list_cache_key,
)


class CacheKeyTests:

    def test_landing_courses_cache_key(self):
        assert landing_courses_cache_key() == "default:landing:courses:list"

    def test_course_list_cache_key_with_user(self):
        key = course_list_cache_key(user_id=42)
        assert key == "default:app:courses:list:42"

    def test_course_list_cache_key_without_user(self):
        key = course_list_cache_key()
        assert key == "default:app:courses:list"

    def test_course_detail_cache_key(self):
        assert course_detail_cache_key("my-slug") == "default:courses:detail:my-slug"

    def test_enrolled_equals_purchased(self):
        assert enrolled_courses_cache_key(5) == purchased_courses_cache_key(5)

    def test_section_list_cache_key(self):
        assert section_list_cache_key("c-slug") == "default:sections:list:c-slug"

    def test_section_detail_cache_key(self):
        assert section_detail_cache_key("c", "s") == "default:sections:detail:c:s"

    def test_lesson_list_cache_key(self):
        assert lesson_list_cache_key("c") == "default:lessons:list:c"

    def test_lesson_detail_cache_key_anon(self):
        key = lesson_detail_cache_key("c", "l")
        assert key == "default:lessons:detail:c:l:pub:anon"

    def test_lesson_detail_cache_key_user(self):
        key = lesson_detail_cache_key("c", "l", scope="all", user_id=7)
        assert key == "default:lessons:detail:c:l:all:7"

    def test_homework_detail_cache_key(self):
        key = homework_detail_cache_key("c", "l", "h")
        assert key == "default:homeworks:detail:c:l:h:pub"

    def test_my_schedule_cache_key_no_dates(self):
        key = my_schedule_cache_key(1)
        assert key == "default:schedule:list:1:none:none"

    def test_attempt_draft_cache_key(self):
        assert attempt_draft_cache_key(3, "hw") == "default:attempt:draft:3:hw"

    def test_attempt_detail_cache_key(self):
        assert attempt_detail_cache_key(99) == "default:attempt:detail:99"

    def test_attempt_list_cache_key_with_user(self):
        assert attempt_list_cache_key("lesson", 5) == "default:attempt:list:lesson:5"

    def test_attempt_list_by_course_cache_key(self):
        key = attempt_list_by_course_cache_key("course-slug", 2)
        assert key == "default:attempt:list:course:course-slug:2"


class CacheInvalidationTests(TestCase):

    def setUp(self):
        self.cache = caches["default"]
        self.cache.clear()

    def tearDown(self):
        self.cache.clear()

    def test_invalidate_on_course_model_change_removes_landing_key(self):
        key = landing_courses_cache_key()
        self.cache.set(key, {"data": "x"})
        invalidate_on_course_model_change("my-course")
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_on_course_model_change_removes_detail_key(self):
        key = course_detail_cache_key("my-course")
        self.cache.set(key, {"data": "x"})
        invalidate_on_course_model_change("my-course")
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_on_section_model_change_removes_keys(self):
        s_list = section_list_cache_key("c")
        s_detail = section_detail_cache_key("c", "s")
        c_detail = course_detail_cache_key("c")
        for k in (s_list, s_detail, c_detail):
            self.cache.set(k, "v")
        invalidate_on_section_model_change("c", "s")
        for k in (s_list, s_detail, c_detail):
            self.assertIsNone(self.cache.get(k), f"{k} should be deleted")

    def test_invalidate_on_lesson_model_change_removes_lesson_list(self):
        key = lesson_list_cache_key("c")
        self.cache.set(key, "v")
        invalidate_on_lesson_model_change("c", "l")
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_on_lesson_model_change_removes_lesson_detail(self):
        key = lesson_detail_cache_key("c", "l")
        self.cache.set(key, "v")
        invalidate_on_lesson_model_change("c", "l")
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_schedule_cache_specific_user(self):
        key = my_schedule_cache_key(10)
        self.cache.set(key, "v")
        invalidate_schedule_cache(user_id=10)
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_user_role_cache_removes_purchased(self):
        key = purchased_courses_cache_key(1)
        self.cache.set(key, "v")
        invalidate_user_role_cache(1)
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_user_role_cache_removes_course_list(self):
        key = course_list_cache_key(1)
        self.cache.set(key, "v")
        invalidate_user_role_cache(1)
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_attempt_cache_removes_draft(self):
        key = attempt_draft_cache_key(1, "hw-slug")
        self.cache.set(key, "v")
        invalidate_attempt_cache(1, "hw-slug", 99, "lesson", "course")
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_attempt_cache_removes_detail(self):
        key = attempt_detail_cache_key(99)
        self.cache.set(key, "v")
        invalidate_attempt_cache(1, "hw-slug", 99, "lesson", "course")
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_attempt_cache_removes_list_by_lesson(self):
        key = attempt_list_cache_key("lesson", 1)
        self.cache.set(key, "v")
        invalidate_attempt_cache(1, "hw-slug", 99, "lesson", "course")
        self.assertIsNone(self.cache.get(key))

    def test_invalidate_attempt_cache_removes_list_by_course(self):
        key = attempt_list_by_course_cache_key("course", 1)
        self.cache.set(key, "v")
        invalidate_attempt_cache(1, "hw-slug", 99, "lesson", "course")
        self.assertIsNone(self.cache.get(key))

    def test_cached_detail_response_stores_value(self):
        key = "test:detail:cached"
        self.cache.delete(key)
        call_count = 0

        def build():
            nonlocal call_count
            call_count += 1
            return {"foo": "bar"}

        resp1 = cached_detail_response(key, build)
        resp2 = cached_detail_response(key, build)

        self.assertEqual(resp1.data, {"foo": "bar"})
        self.assertEqual(resp2.data, {"foo": "bar"})
        self.assertEqual(call_count, 1, "build() must be called only once when cache hits")
