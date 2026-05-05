from functools import lru_cache

from django.conf import settings

from .asset_service import AssetService
from .facades.access_api import AccessApi
from .facades.binding_api import BindingApi
from .facades.upload_api import UploadApi
from .facades.worker_api import WorkerApi
from .storages.external import ExternalBackend
from .storages.kinescope import KinescopeBackend
from .storages.s3 import S3Backend


@lru_cache(maxsize=1)
def _get_backends():
    backends = {}

    if getattr(settings, 'USE_S3', False):
        backends['s3'] = S3Backend(
            bucket=settings.AWS_S3_BUCKET_NAME,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            region_name=settings.AWS_S3_REGION_NAME,
        )

    backends['kinescope'] = KinescopeBackend(
        api_key=getattr(settings, 'KINESCOPE_API_TOKEN', ''),
        project_id=getattr(settings, 'KINESCOPE_PROJECT_ID', ''),
    )

    backends['external'] = ExternalBackend()

    return backends


def reset_backends_cache():
    _get_backends.cache_clear()


def build_asset_service():
    return AssetService(backends=_get_backends())


def build_upload_api():
    return UploadApi(asset_service=build_asset_service())


def build_binding_api():
    return BindingApi(asset_service=build_asset_service())


def build_access_api():
    return AccessApi(asset_service=build_asset_service())


def build_worker_api():
    return WorkerApi(asset_service=build_asset_service())
