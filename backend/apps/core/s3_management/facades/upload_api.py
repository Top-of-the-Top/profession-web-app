from ...models import AssetStatus
from ..dto import InitiateResult
from ..errors import AssetPermissionDenied


class UploadApi:

    def __init__(self, asset_service):
        self._service = asset_service

    def initiate_upload(self, user, intent, filename, mime_type, size, sha256=''):
        asset, dedup = self._service.create_pending_asset(
            owner=user,
            intent=intent,
            filename=filename,
            mime_type=mime_type,
            size=size,
            sha256=sha256,
        )

        if dedup:
            return InitiateResult(
                asset_id=str(asset.asset_id),
                dedup=True,
                storage_backend=asset.storage_backend,
                upload=None,
            )

        upload = self._service.issue_upload_url(asset, intent)
        return InitiateResult(
            asset_id=str(asset.asset_id),
            dedup=False,
            storage_backend=asset.storage_backend,
            upload=upload,
        )

    def get_upload_status(self, user, asset_id):
        return self._authorize(user, asset_id)

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
