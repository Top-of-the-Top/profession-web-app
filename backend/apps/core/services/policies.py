MB = 1024 * 1024


INTENT_POLICIES = {
    'homework_attachment': {
        'backend': 's3',
        'max_size': 10 * MB,
        'mime_allowlist': (
            'application/pdf',
            'application/zip',
            'image/png',
            'image/jpeg',
            'text/plain',
        ),
        'default_visibility': 'private',
        'default_role': 'task_attachment',
    },
    'homework_material': {
        'backend': 's3',
        'max_size': 10 * MB,
        'mime_allowlist': (
            'application/pdf',
            'application/zip',
            'image/png',
            'image/jpeg',
            'text/plain',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'audio/mpeg',
            'video/mp4',
        ),
        'default_visibility': 'course_paid',
        'default_role': 'homework_material',
    },
    'lesson_image': {
        'backend': 's3',
        'max_size': 10 * MB,
        'mime_allowlist': (
            'image/png',
            'image/jpeg',
            'image/webp',
            'image/gif',
            'image/svg+xml',
        ),
        'default_visibility': 'course_paid',
        'default_role': 'lesson_block',
    },
    'lesson_file': {
        'backend': 's3',
        'max_size': 100 * MB,
        'mime_allowlist': (
            'application/pdf',
            'application/zip',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
        ),
        'default_visibility': 'course_paid',
        'default_role': 'lesson_block',
    },
    'course_cover': {
        'backend': 's3',
        'max_size': 10 * MB,
        'mime_allowlist': (
            'image/png',
            'image/jpeg',
            'image/webp',
        ),
        'default_visibility': 'public',
        'default_role': 'course_cover',
    },
    'user_avatar': {
        'backend': 's3',
        'max_size': 10 * MB,
        'mime_allowlist': (
            'image/png',
            'image/jpeg',
        ),
        'default_visibility': 'public',
        'default_role': 'user_avatar',
    },
    'webinar_whiteboard': {
        'backend': 's3',
        'max_size': 50 * MB,
        'mime_allowlist': (
            'application/pdf',
        ),
        'default_visibility': 'course_paid',
        'default_role': 'whiteboard_pdf',
    },
}


BIND_POLICIES = {
    'task_attachment': {
        'max_usages_per_target': None,
        'allowed_backends': ('s3',),
    },
    'homework_material': {
        'max_usages_per_target': None,
        'allowed_backends': ('s3',),
    },
    'lesson_block': {
        'max_usages_per_target': None,
        'allowed_backends': ('s3', 'kinescope'),
    },
    'course_cover': {
        'max_usages_per_target': 1,
        'allowed_backends': ('s3',),
    },
    'webinar_recording': {
        'max_usages_per_target': 1,
        'allowed_backends': ('kinescope',),
    },
    'user_avatar': {
        'max_usages_per_target': 1,
        'allowed_backends': ('s3',),
    },
    'whiteboard_pdf': {
        'max_usages_per_target': 1,
        'allowed_backends': ('s3',),
    },
}


def get_intent_policy(intent):
    return INTENT_POLICIES.get(intent)


def get_bind_policy(role):
    return BIND_POLICIES.get(role)
