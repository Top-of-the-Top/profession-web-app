from ...models import AssetStatus
from ..dto import InitiateResult
from ..errors import AssetPermissionDenied


class UploadApi:

    def __init__(self, asset_service):
        self._service = asset_service

    def initiate_upload(self, user, intent, filename, mime_type, size):
        asset = self._service.create_pending_asset(
            owner=user,
            intent=intent,
            filename=filename,
            mime_type=mime_type,
            size=size,
        )

        upload = self._service.issue_upload_url(asset, intent)
        return InitiateResult(
            asset_id=str(asset.asset_id),
            dedup=False,
            storage_backend=asset.storage_backend,
            upload=upload,
        )

    def get_upload_status(self, user, asset_id):
        asset = self._authorize(user, asset_id)
        if asset.status == AssetStatus.PENDING:
            self._try_trigger_commit(asset)
        return asset

    def _try_trigger_commit(self, asset):
        try:
            backend = self._service.get_backend(asset.storage_backend)
            meta = backend.head(asset.storage_key)
            if meta is not None:
                from ..tasks import commit_pending_asset
                # Фиксированный task_id гарантирует что Celery не запустит
                # дублирующую задачу если фронт поллит часто
                commit_pending_asset.apply_async(
                    args=[str(asset.asset_id)],
                    task_id=f'commit-{asset.asset_id}',
                )
        except Exception:
            pass

    def commit_for_user(self, user, asset_id):
        asset = self._authorize(user, asset_id)
        if asset.status == AssetStatus.READY:
            return asset
        return self._service.commit_asset(asset.asset_id)

    def upload_server_side(self, owner, intent, filename, mime_type, body):
        return self._service.register_server_asset(
            owner=owner,
            intent=intent,
            filename=filename,
            mime_type=mime_type,
            body=body,
        )

    def _authorize(self, user, asset_id):
        asset = self._service.get_asset(asset_id)

        if user is None:
            raise AssetPermissionDenied(details={'asset_id': str(asset_id)})

        is_owner = asset.owner_id == getattr(user, 'pk', None)
        is_staff = getattr(user, 'is_staff', False)

        if not is_owner and not is_staff:
            raise AssetPermissionDenied(details={'asset_id': str(asset_id)})

        return asset
