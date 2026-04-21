from ..errors import AssetStorageUnavailable
from .base import StorageBackend


class KinescopeBackend(StorageBackend):

    name = 'kinescope'

    def __init__(self, api_key='', base_url='https://api.kinescope.io'):
        self._api_key = api_key
        self._base_url = base_url

    def build_storage_key(self, hint):
        raise AssetStorageUnavailable(
            message='Kinescope backend ещё не реализован.',
            details={'stage': 'build_storage_key'},
        )

    def issue_presigned_upload(self, storage_key, policy):
        raise AssetStorageUnavailable(
            message='Kinescope backend ещё не реализован.',
            details={'stage': 'issue_presigned_upload'},
        )

    def head(self, storage_key):
        raise AssetStorageUnavailable(
            message='Kinescope backend ещё не реализован.',
            details={'stage': 'head'},
        )

    def delete(self, storage_key):
        raise AssetStorageUnavailable(
            message='Kinescope backend ещё не реализован.',
            details={'stage': 'delete'},
        )

    def resolve_url(self, asset, viewer=None, ttl_seconds=300):
        raise AssetStorageUnavailable(
            message='Kinescope backend ещё не реализован.',
            details={'stage': 'resolve_url'},
        )

    def stream_read(self, storage_key, chunk_size=1024 * 1024):
        raise AssetStorageUnavailable(
            message='Kinescope backend ещё не реализован.',
            details={'stage': 'stream_read'},
        )
