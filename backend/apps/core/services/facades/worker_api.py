import logging
from datetime import timedelta

from django.utils import timezone

from ...models import AssetStatus, MediaAsset


logger = logging.getLogger(__name__)


class WorkerApi:

    def __init__(self, asset_service):
        self._service = asset_service

    def commit_by_id(self, asset_id):
        return self._service.commit_asset(asset_id)

    def commit_by_storage_key(self, storage_key, backend='s3'):
        asset = self._service.get_asset_by_storage_key(storage_key, backend=backend)
        if asset is None:
            return None
        if asset.status != AssetStatus.PENDING:
            return asset
        return self._service.commit_asset(asset.asset_id)

    def physical_delete(self, asset_id):
        asset = self._service.get_asset(asset_id)

        if asset.status == AssetStatus.DELETED:
            return {'status': 'already_deleted'}

        if asset.ref_count > 0:
            return {'status': 'still_referenced'}

        backend = self._service.get_backend(asset.storage_backend)
        backend.delete(asset.storage_key)

        MediaAsset.objects.filter(pk=asset_id).update(
            status=AssetStatus.DELETED,
            deleted_at=timezone.now(),
        )
        return {'status': 'deleted'}

    def sweep_pending(self, pending_ttl_hours=24, batch_size=200):
        pending = MediaAsset.objects.filter(
            status=AssetStatus.PENDING,
        ).order_by('created_at')[:batch_size]

        expired_cutoff = timezone.now() - timedelta(hours=pending_ttl_hours)
        committed = 0
        expired = 0

        for asset in pending:
            try:
                backend = self._service.get_backend(asset.storage_backend)
                meta = backend.head(asset.storage_key)
            except Exception:
                logger.exception('sweep_pending: head failed для %s', asset.asset_id)
                continue

            if meta is not None:
                try:
                    self._service.commit_asset(str(asset.asset_id))
                    committed += 1
                except Exception:
                    logger.exception('sweep_pending: commit failed для %s', asset.asset_id)
                continue

            if asset.created_at < expired_cutoff:
                MediaAsset.objects.filter(pk=asset.asset_id).update(
                    status=AssetStatus.DELETED,
                    deleted_at=timezone.now(),
                )
                expired += 1

        return {'committed': committed, 'expired': expired}

    def find_orphaned(self, grace_days=7, batch_size=500):
        threshold = timezone.now() - timedelta(days=grace_days)
        return list(
            MediaAsset.objects
            .filter(
                status=AssetStatus.READY,
                ref_count=0,
                unreferenced_since__isnull=False,
                unreferenced_since__lt=threshold,
            )
            .values_list('asset_id', flat=True)[:batch_size]
        )
