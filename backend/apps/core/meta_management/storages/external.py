from django.utils import timezone

from ..dto import ObjectMeta
from ..errors import AssetStorageUnavailable
from .base import StorageBackend


class ExternalBackend(StorageBackend):

    name = 'external'

    def build_storage_key(self, hint):
        raise AssetStorageUnavailable(
            message='Внешние ссылки создаются через register_external(url), а не через initiate.',
            details={'stage': 'build_storage_key'},
        )

    def issue_presigned_upload(self, storage_key, policy, storage_meta=None):
        raise AssetStorageUnavailable(
            message='Для external backend загрузка через presigned URL невозможна.',
            details={'stage': 'issue_presigned_upload'},
        )

    def head(self, storage_key):
        return ObjectMeta(
            key=storage_key,
            size_bytes=0,
            etag='',
            last_modified=timezone.now(),
            mime_type='',
        )

    def delete(self, storage_key):
        return None

    def resolve_url(self, asset, viewer=None, ttl_seconds=300):
        return asset.storage_key

    def put_object(self, storage_key, body, mime_type=''):
        raise AssetStorageUnavailable(
            message='External backend не поддерживает put_object.',
            details={'stage': 'put_object'},
        )
