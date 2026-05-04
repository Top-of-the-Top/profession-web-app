from django.contrib.contenttypes.models import ContentType

from .factory import build_access_api
from ..models import AssetUsage, AssetStatus


def _build_assets_for_object(obj, roles, viewer=None):
    if obj is None or obj.pk is None:
        return {role: [] for role in roles}

    content_type = ContentType.objects.get_for_model(obj)
    object_id = str(obj.pk)

    usages = (
        AssetUsage.objects
        .filter(
            content_type=content_type,
            object_id=object_id,
            role__in=roles,
            asset__status=AssetStatus.READY,
        )
        .select_related('asset')
        .order_by('created_at')
    )

    access = build_access_api()
    result = {role: [] for role in roles}

    for usage in usages:
        asset = usage.asset
        try:
            url = access.resolve_asset_url(asset, viewer=viewer)
        except Exception:
            url = None

        result.setdefault(usage.role, []).append({
            'asset_id': str(asset.asset_id),
            'filename': asset.original_filename or '',
            'mime_type': asset.mime_type or '',
            'size_bytes': asset.size_bytes or 0,
            'url': url,
        })

    return result


class AssetsSerializerMixin:
    """
    Подмешивается в ModelSerializer.
    Подкласс объявляет:
        asset_roles = ['course_cover']           # какие роли включать
    Автоматически добавляет поле assets в ответ GET.
    При записи (create/update) ищет поля вида <role>_asset_id / <role>_asset_ids
    и синкает привязки через BindingApi.
    """

    asset_roles: list = []

    def get_assets(self, obj):
        request = self.context.get('request')
        viewer = getattr(request, 'user', None) if request is not None else None
        return _build_assets_for_object(obj, self.asset_roles, viewer=viewer)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['assets'] = self.get_assets(instance)
        return ret

    def _sync_asset_fields(self, instance):
        """
        После save() синкает все asset_id поля которые пришли в validated_data.
        Поле <role>_asset_id  → sync_single (один ассет, например обложка)
        Поле <role>_asset_ids → sync_many   (список, например материалы)
        """
        from .factory import build_binding_api

        data = getattr(self, '_assets_to_sync', {})
        if not data:
            return

        request = self.context.get('request')
        owner = getattr(request, 'user', None) if request is not None else None
        binding = build_binding_api()

        for role, (mode, value) in data.items():
            if mode == 'single':
                binding.sync_single(
                    content_object=instance,
                    role=role,
                    asset_id=value,
                    owner=owner,
                )
            elif mode == 'many':
                binding.sync_many(
                    content_object=instance,
                    role=role,
                    asset_ids=value,
                    owner=owner,
                )

        self._assets_to_sync = {}

    def _extract_asset_fields(self, validated_data):
        """
        Вытаскивает из validated_data поля *_asset_id / *_asset_ids,
        сохраняет для последующего _sync_asset_fields().
        """
        self._assets_to_sync = {}
        for role in self.asset_roles:
            single_key = f'{role}_asset_id'
            many_key = f'{role}_asset_ids'
            if single_key in validated_data:
                self._assets_to_sync[role] = ('single', validated_data.pop(single_key))
            elif many_key in validated_data:
                self._assets_to_sync[role] = ('many', validated_data.pop(many_key))

    def create(self, validated_data):
        self._extract_asset_fields(validated_data)
        instance = super().create(validated_data)
        self._sync_asset_fields(instance)
        return instance

    def update(self, instance, validated_data):
        self._extract_asset_fields(validated_data)
        instance = super().update(instance, validated_data)
        self._sync_asset_fields(instance)
        return instance
