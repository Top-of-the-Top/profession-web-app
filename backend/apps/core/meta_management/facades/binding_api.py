from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from ...models import AssetStatus, AssetUsage
from ..errors import AssetPermissionDenied


class BindingApi:
    def __init__(self, asset_service):
        self._service = asset_service

    def bind_for_user(self, user, asset_id, content_object, role):
        asset = self._service.get_asset(asset_id)

        if user is None or asset.owner_id != getattr(user, "pk", None):
            raise AssetPermissionDenied(details={"asset_id": str(asset_id)})

        asset = self._ensure_committed(asset)

        return self._service.bind_asset(asset, content_object, role)

    def unbind_for_user(self, user, usage_id):
        usage = self._service.get_usage(usage_id)

        if user is not None and usage.asset.owner_id != getattr(user, "pk", None):
            raise AssetPermissionDenied(details={"usage_id": str(usage_id)})

        self._service.unbind_usage(usage)

    def sync_single(self, content_object, role, asset_id, owner):
        target_ids = {str(asset_id)} if asset_id else set()
        self._sync(content_object, role, target_ids, owner)

    def sync_many(self, content_object, role, asset_ids, owner):
        target_ids = {str(x) for x in (asset_ids or []) if x}
        self._sync(content_object, role, target_ids, owner)

    def _ensure_committed(self, asset):
        if asset.status == AssetStatus.PENDING:
            return self._service.commit_asset(asset.asset_id)
        return asset

    def _sync(self, content_object, role, target_ids, owner):
        content_type = ContentType.objects.get_for_model(content_object)
        object_id = str(content_object.pk)

        existing = list(
            AssetUsage.objects.filter(
                content_type=content_type, object_id=object_id, role=role
            ).select_related("asset")
        )
        existing_by_asset = {str(u.asset_id): u for u in existing}
        existing_ids = set(existing_by_asset.keys())

        to_remove = existing_ids - target_ids
        to_add = target_ids - existing_ids

        assets_to_bind = []
        for asset_id in to_add:
            asset = self._service.get_asset(asset_id)
            if owner is not None and asset.owner_id != getattr(owner, "pk", None):
                raise AssetPermissionDenied(details={"asset_id": asset_id})
            asset = self._ensure_committed(asset)
            assets_to_bind.append(asset)

        with transaction.atomic():
            for asset_id in to_remove:
                self._service.unbind_usage(existing_by_asset[asset_id])

            for asset in assets_to_bind:
                self._service.bind_asset(asset, content_object, role)
