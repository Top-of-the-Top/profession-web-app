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

    def register_external(self, owner, url, intent):
        return self._service.register_external_asset(owner=owner, url=url, intent=intent)
