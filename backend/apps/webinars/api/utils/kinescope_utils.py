"""
Обратная совместимость импортов: все вызовы Kinescope идут через
`apps.core.meta_management` (KinescopeBackend + factory).
"""

from apps.core.meta_management.factory import build_asset_service
from apps.core.meta_management.storages.kinescope import KinescopeBackend


def _backend() -> KinescopeBackend:
    return build_asset_service().get_backend("kinescope")


def create_folder(name, project_id=None):
    return _backend().create_folder(name, project_id=project_id)


def upload_video_by_url(video_url, title, parent_id=None):
    video_id = _backend().upload_by_url(video_url, title, parent_id=parent_id)
    return {"id": video_id} if video_id else {}


def get_video_status(video_id):
    return _backend().get_video_payload(video_id)


def generate_drm_token(user_id, video_id, lifetime_seconds=3600):
    return KinescopeBackend.generate_drm_token(user_id, video_id, lifetime_seconds)


def setup_drm_auth(callback_url, username, password, strict=True):
    return _backend().configure_drm_auth(callback_url, username, password, strict=strict)
