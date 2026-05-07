from django.contrib.contenttypes.models import ContentType

from ...models import AssetStatus, AssetUsage, MediaAsset


class AccessApi:
    def __init__(self, asset_service):
        self._service = asset_service

    def resolve_for_viewer(self, asset_id, viewer=None, ttl_seconds=300):
        asset = self._service.get_asset(asset_id)
        return self._service.resolve_asset_url(
            asset,
            viewer=viewer,
            ttl_seconds=ttl_seconds,
        )

    def resolve_many_for_viewer(self, asset_ids, viewer=None, ttl_seconds=300):
        ids = [str(x).lower() for x in (asset_ids or []) if x]
        if not ids:
            return {}

        assets = MediaAsset.objects.filter(
            asset_id__in=ids,
            status=AssetStatus.READY,
        )
        by_id = {str(a.asset_id).lower(): a for a in assets}

        result = {}
        for asset_id in ids:
            asset = by_id.get(asset_id)
            if asset is None:
                result[asset_id] = None
                continue
            try:
                result[asset_id] = self._service.resolve_asset_url(
                    asset,
                    viewer=viewer,
                    ttl_seconds=ttl_seconds,
                )
            except Exception:
                result[asset_id] = None
        return result

    def get_bound_asset(self, content_object, role):
        if content_object is None or content_object.pk is None:
            return None

        content_type = ContentType.objects.get_for_model(content_object)
        usage = (
            AssetUsage.objects.filter(
                content_type=content_type,
                object_id=str(content_object.pk),
                role=role,
            )
            .select_related("asset")
            .first()
        )

        if usage is None:
            return None
        if usage.asset.status != AssetStatus.READY:
            return None

        return usage.asset

    def resolve_bound_url(self, content_object, role, viewer=None, ttl_seconds=300):
        asset = self.get_bound_asset(content_object, role)
        if asset is None:
            return None
        return self._service.resolve_asset_url(asset, viewer=viewer, ttl_seconds=ttl_seconds)

    def resolve_bound_urls_map(self, content_objects, role, viewer=None, ttl_seconds=300):
        objects = [o for o in (content_objects or []) if o is not None and o.pk is not None]
        if not objects:
            return {}

        content_type = ContentType.objects.get_for_model(type(objects[0]))
        object_ids = [str(o.pk) for o in objects]

        usages = AssetUsage.objects.filter(
            content_type=content_type,
            object_id__in=object_ids,
            role=role,
        ).select_related("asset")

        asset_by_object_id = {}
        for usage in usages:
            if usage.asset.status != AssetStatus.READY:
                continue
            asset_by_object_id.setdefault(str(usage.object_id), usage.asset)

        result = {}
        for obj in objects:
            key = str(obj.pk)
            asset = asset_by_object_id.get(key)
            if asset is None:
                result[key] = None
                continue
            try:
                result[key] = self._service.resolve_asset_url(
                    asset,
                    viewer=viewer,
                    ttl_seconds=ttl_seconds,
                )
            except Exception:
                result[key] = None

        return result

    def resolve_bound_assets_map(self, content_objects, role, viewer=None, ttl_seconds=300):
        objects = [o for o in (content_objects or []) if o is not None and o.pk is not None]
        if not objects:
            return {}

        content_type = ContentType.objects.get_for_model(type(objects[0]))
        object_ids = [str(o.pk) for o in objects]

        usages = (
            AssetUsage.objects.filter(
                content_type=content_type,
                object_id__in=object_ids,
                role=role,
            )
            .select_related("asset")
            .order_by("created_at")
        )

        result = {key: [] for key in object_ids}
        for usage in usages:
            asset = usage.asset
            if asset.status != AssetStatus.READY:
                continue
            try:
                url = self._service.resolve_asset_url(
                    asset,
                    viewer=viewer,
                    ttl_seconds=ttl_seconds,
                )
            except Exception:
                url = None
            result.setdefault(str(usage.object_id), []).append(
                {
                    "asset": asset,
                    "url": url,
                }
            )
        return result

    def register_external(self, owner, url, intent):
        return self._service.register_external_asset(owner=owner, url=url, intent=intent)
