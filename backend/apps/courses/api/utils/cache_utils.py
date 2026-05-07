from django.core.cache import caches
from rest_framework.response import Response


DEFAULT_CACHE_ALIAS = 'default'


def delete_cache_keys(cache_alias, *keys):
    cache = caches[cache_alias]
    for key in keys:
        if key is not None:
            cache.delete(key)


def default_cache():
    return caches[DEFAULT_CACHE_ALIAS]


def landing_courses_cache_key():
    return "default:landing:courses:list"


def course_list_cache_key(user_id=None):
    if user_id is not None:
        return f"default:app:courses:list:{int(user_id)}"
    return "default:app:courses:list"


def course_detail_cache_key(slug):
    return f"default:courses:detail:{slug}"


def purchased_courses_cache_key(user_id):
    return f"default:courses:purchased:{int(user_id)}"


def section_list_cache_key(course_slug):
    return f"default:sections:list:{course_slug}"


def section_detail_cache_key(course_slug, slug):
    return f"default:sections:detail:{course_slug}:{slug}"


def lesson_list_cache_key(course_slug):
    return f"default:lessons:list:{course_slug}"


def my_schedule_cache_key(user_id, start_date=None, end_date=None):
    start = start_date.isoformat() if start_date else 'none'
    end = end_date.isoformat() if end_date else 'none'
    return f"default:schedule:list:{int(user_id)}:{start}:{end}"


DETAIL_CACHE_SCOPES = ('pub', 'all')


def lesson_detail_cache_key(course_slug, slug, scope='pub'):
    return f"default:lessons:detail:{course_slug}:{slug}:{scope}"


def homework_detail_cache_key(course_slug, lesson_slug, slug, scope='pub'):
    return f"default:homeworks:detail:{course_slug}:{lesson_slug}:{slug}:{scope}"


def invalidate_lesson_detail_cache(course_slug, lesson_slug):
    c = default_cache()
    for scope in DETAIL_CACHE_SCOPES:
        c.delete(lesson_detail_cache_key(course_slug, lesson_slug, scope))


def invalidate_homework_detail_cache(course_slug, lesson_slug, homework_slug):
    c = default_cache()
    for scope in DETAIL_CACHE_SCOPES:
        c.delete(
            homework_detail_cache_key(course_slug, lesson_slug, homework_slug, scope)
        )


def invalidate_on_course_model_change(slug):
    delete_cache_keys(
        DEFAULT_CACHE_ALIAS,
        landing_courses_cache_key(),
        course_detail_cache_key(slug),
        course_list_cache_key(),
    )
    cache = caches[DEFAULT_CACHE_ALIAS]
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern('default:app:courses:list:*')


def invalidate_on_section_model_change(course_slug, section_slug):
    delete_cache_keys(
        DEFAULT_CACHE_ALIAS,
        section_list_cache_key(course_slug),
        section_detail_cache_key(course_slug, section_slug),
        course_detail_cache_key(course_slug),
    )


def invalidate_on_lesson_model_change(course_slug, lesson_slug):
    delete_cache_keys(
        DEFAULT_CACHE_ALIAS,
        lesson_list_cache_key(course_slug),
        course_detail_cache_key(course_slug),
    )
    invalidate_lesson_detail_cache(course_slug, lesson_slug)


def invalidate_on_homework_tree_change(course_slug, lesson_slug, homework_slug):
    invalidate_lesson_detail_cache(course_slug, lesson_slug)
    invalidate_homework_detail_cache(course_slug, lesson_slug, homework_slug)
    default_cache().delete(course_detail_cache_key(course_slug))


def cached_detail_response(cache_key, build_data):
    cache = default_cache()
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)
    data = build_data()
    cache.set(cache_key, data)
    return Response(data)


def invalidate_user_role_cache(user_id):
    uid = int(user_id)
    cache = default_cache()
    cache.delete(course_list_cache_key(uid))
    cache.delete(purchased_courses_cache_key(uid))
    cache.delete(my_schedule_cache_key(uid))


def attempt_draft_cache_key(user_id, homework_slug):
    return f"default:attempt:draft:{int(user_id)}:{homework_slug}"


def attempt_detail_cache_key(attempt_id):
    return f"default:attempt:detail:{attempt_id}"


def attempt_list_cache_key(lesson_slug, user_id=None):
    if user_id is not None:
        return f"default:attempt:list:{lesson_slug}:{int(user_id)}"
    return f"default:attempt:list:{lesson_slug}"


def attempt_list_by_course_cache_key(course_slug, user_id=None):
    if user_id is not None:
        return f"default:attempt:list:course:{course_slug}:{int(user_id)}"
    return f"default:attempt:list:course:{course_slug}"


def _delete(cache, *keys):
    for key in keys:
        cache.delete(key)


def _delete_pattern_or_key(cache, pattern, fallback_key):
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(pattern)
    else:
        cache.delete(fallback_key)


def invalidate_attempt_cache(user_id, homework_slug, attempt_id, lesson_slug, course_slug):
    cache = default_cache()
    uid = int(user_id)

    _delete(
        cache,
        attempt_draft_cache_key(uid, homework_slug),
        attempt_detail_cache_key(attempt_id),
    )

    _delete_pattern_or_key(
        cache,
        f'default:attempt:list:{lesson_slug}:*',
        attempt_list_cache_key(lesson_slug, uid),
    )
    cache.delete(attempt_list_cache_key(lesson_slug))

    _delete_pattern_or_key(
        cache,
        f'default:attempt:list:course:{course_slug}:*',
        attempt_list_by_course_cache_key(course_slug, uid),
    )
    cache.delete(attempt_list_by_course_cache_key(course_slug))

    _delete_pattern_or_key(
        cache,
        'default:attempt:list:all:*',
        f'default:attempt:list:all:{uid}',
    )
    cache.delete('default:attempt:list:all')


def invalidate_student_homework_list_cache(lesson_slug, course_slug):
    cache = default_cache()
    _delete_pattern_or_key(
        cache,
        f'default:attempt:list:{lesson_slug}:*',
        attempt_list_cache_key(lesson_slug),
    )
    _delete_pattern_or_key(
        cache,
        f'default:attempt:list:course:{course_slug}:*',
        attempt_list_by_course_cache_key(course_slug),
    )
    _delete_pattern_or_key(
        cache,
        'default:attempt:list:all:*',
        'default:attempt:list:all',
    )
