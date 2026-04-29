import os
from django.core.management.base import BaseCommand
from apps.webinars.api.utils.kinescope_utils import setup_drm_auth


class Command(BaseCommand):
    help = 'Регистрация DRM auth callback URL в Kinescope'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            required=True,
            help='Полный URL callback-эндпоинта (например: https://professionkid.ru/api/kinescope/drm-auth/)',
        )
        parser.add_argument(
            '--username',
            default=None,
            help='Логин для Basic Auth (по умолчанию из KINESCOPE_DRM_AUTH_USERNAME)',
        )
        parser.add_argument(
            '--password',
            default=None,
            help='Пароль для Basic Auth (по умолчанию из KINESCOPE_DRM_AUTH_PASSWORD)',
        )

    def handle(self, *args, **options):
        username = options['username'] or os.getenv('KINESCOPE_DRM_AUTH_USERNAME', '')
        password = options['password'] or os.getenv('KINESCOPE_DRM_AUTH_PASSWORD', '')

        result = setup_drm_auth(
            callback_url=options['url'],
            username=username,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f'DRM auth зарегистрирован: {result}'))
