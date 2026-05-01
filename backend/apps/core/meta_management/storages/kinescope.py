import logging
import time
from datetime import timedelta

import jwt
import requests
from django.conf import settings
from django.utils import timezone

from ..dto import ObjectMeta, PresignedUpload
from ..errors import AssetStorageUnavailable
from .base import StorageBackend


logger = logging.getLogger(__name__)

API_BASE = 'https://api.kinescope.io/v1'
UPLOADER_BASE = 'https://uploader.kinescope.io/v2'
EMBED_URL_TEMPLATE = 'https://kinescope.io/embed/{video_id}'

# Видео загружено когда Kinescope вернул processing или ready
UPLOADED_STATUSES = {'processing', 'ready'}


class KinescopeBackend(StorageBackend):

    name = 'kinescope'

    def __init__(self, api_key, project_id=''):
        self._project_id = project_id
        self._session = requests.Session()
        self._session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        })

        self._pending_upload_links: dict[str, str] = {}

    def _post(self, path, base=None, extra_headers=None, json=None):
        url = f'{base or API_BASE}{path}'
        try:
            resp = self._session.post(url, headers=extra_headers, json=json, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error('Kinescope POST %s failed: %s', url, exc)
            raise AssetStorageUnavailable(
                message='Kinescope API недоступен.',
                details={'path': path},
            )

    def _get(self, path):
        try:
            resp = self._session.get(f'{API_BASE}{path}', timeout=10)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error('Kinescope GET %s failed: %s', path, exc)
            raise AssetStorageUnavailable(
                message='Kinescope API недоступен.',
                details={'path': path},
            )

    def _delete(self, path):
        try:
            resp = self._session.delete(f'{API_BASE}{path}', timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error('Kinescope DELETE %s failed: %s', path, exc)
            raise AssetStorageUnavailable(
                message='Kinescope API недоступен.',
                details={'path': path},
            )

    def build_storage_key(self, hint):
        """Создаёт видео-placeholder в Kinescope, возвращает video_id."""
        endpoint = (
            f'/projects/{self._project_id}/videos'
            if self._project_id
            else '/videos'
        )
        payload = {'title': hint.filename or 'video'}
        data = self._post(endpoint, json=payload, base=API_BASE)

        video = data.get('data', {})
        video_id = video.get('id')
        upload_link = video.get('upload_link', '')

        if not video_id:
            raise AssetStorageUnavailable(
                message='Kinescope не вернул video_id.',
                details={'response': data},
            )

        self._pending_upload_links[video_id] = upload_link
        return video_id

    def issue_presigned_upload(self, storage_key, policy):
        upload_link = self._pending_upload_links.pop(storage_key, '')

        if not upload_link:
            data = self._get(f'/videos/{storage_key}')
            if data:
                upload_link = data.get('data', {}).get('upload_link', '')

        if not upload_link:
            raise AssetStorageUnavailable(
                message='Не удалось получить upload URL от Kinescope.',
                details={'video_id': storage_key},
            )

        return PresignedUpload(
            method='POST',
            url=upload_link,
            storage_key=storage_key,
            expires_at=timezone.now() + timedelta(hours=24),
            fields={},
            headers={},
        )

    def head(self, storage_key):
        data = self._get(f'/videos/{storage_key}')
        if data is None:
            return None

        video = data.get('data', {})
        status = video.get('status', '')

        if status not in UPLOADED_STATUSES:
            return None

        return ObjectMeta(
            key=storage_key,
            size_bytes=video.get('size', 0) or 0,
            etag='',
            last_modified=timezone.now(),
            mime_type='video/mp4',
        )

    def delete(self, storage_key):
        self._delete(f'/videos/{storage_key}')

    def resolve_url(self, asset, viewer=None, ttl_seconds=300):
        """Embed URL с DRM-токеном для авторизованных пользователей."""
        base = EMBED_URL_TEMPLATE.format(video_id=asset.storage_key)
        token = self._drm_token(viewer, asset.storage_key, ttl_seconds)
        return f'{base}?token={token}' if token else base

    def put_object(self, storage_key, body, mime_type=''):
        raise AssetStorageUnavailable(
            message='Kinescope не поддерживает прямую загрузку байт. '
                    'Используйте upload_by_url() для серверной загрузки.',
            details={'stage': 'put_object'},
        )

    # ------------------------------------------------------------------ #
    # Kinescope-специфичные методы (не входят в StorageBackend interface) #
    # ------------------------------------------------------------------ #

    def upload_by_url(self, video_url, title, parent_id=None):
        """
        Загружает видео по URL — Kinescope сам скачивает файл.
        Используется для записей вебинаров (Agora recording URL → Kinescope).
        Возвращает video_id.
        """
        data = self._post(
            '/video',
            base=UPLOADER_BASE,
            extra_headers={
                'X-Parent-ID': parent_id or self._project_id or '',
                'X-Video-Title': title,
                'X-Video-URL': video_url,
            },
        )
        video_id = (data.get('data') or {}).get('id', '')
        if not video_id:
            raise AssetStorageUnavailable(
                message='Kinescope не вернул video_id при загрузке по URL.',
                details={'video_url': video_url},
            )
        return video_id

    def _drm_token(self, viewer, video_id, ttl_seconds):
        """JWT для DRM-защищённого просмотра, подписанный SECRET_KEY."""
        if viewer is None:
            return None
        try:
            payload = {
                'user_id': str(getattr(viewer, 'pk', '')),
                'video_id': video_id,
                'exp': int(time.time()) + ttl_seconds,
                'token_type': 'kinescope_drm',
            }
            return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        except Exception as exc:
            logger.warning('Kinescope DRM token error: %s', exc)
            return None
