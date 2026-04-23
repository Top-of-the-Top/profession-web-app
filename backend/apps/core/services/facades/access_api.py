from django.contrib.contenttypes.models import ContentType

from ...models import AssetStatus, AssetUsage


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
        result = {}
        for asset_id in asset_ids:
            try:
                result[str(asset_id)] = self.resolve_for_viewer(
                    asset_id,
                    viewer=viewer,
                    ttl_seconds=ttl_seconds,
                )
            except Exception:
                result[str(asset_id)] = None
        return result

    def get_bound_asset(self, content_object, role):
        if content_object is None or content_object.pk is None:
            return None

        content_type = ContentType.objects.get_for_model(content_object)
        usage = (
            AssetUsage.objects
            .filter(
                content_type=content_type,
                object_id=str(content_object.pk),
                role=role,
            )
            .select_related('asset')
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

        usages = (
            AssetUsage.objects
            .filter(
                content_type=content_type,
                object_id__in=object_ids,
                role=role,
            )
            .select_related('asset')
        )

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

    def register_external(self, owner, url, intent):
        return self._service.register_external_asset(owner=owner, url=url, intent=intent)
