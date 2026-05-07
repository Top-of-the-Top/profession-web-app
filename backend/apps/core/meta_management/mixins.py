from django.contrib.contenttypes.models import ContentType

from .factory import build_asset_service
from ..models import AssetUsage, AssetStatus


def _build_assets_batch(objects, roles, viewer=None):
    """
    Один запрос к AssetUsage для всего списка объектов.
    Возвращает {str(pk): {role: [{asset_id, filename, mime_type, size_bytes, url}]}}
    """
    if not objects or not roles:
        return {}

    content_type = ContentType.objects.get_for_model(type(objects[0]))
    object_ids = [str(o.pk) for o in objects]

    usages = (
        AssetUsage.objects
        .filter(
            content_type=content_type,
            object_id__in=object_ids,
            role__in=roles,
            asset__status=AssetStatus.READY,
        )
        .select_related('asset')
        .order_by('created_at')
    )

    service = build_asset_service()
    result = {pk: {role: [] for role in roles} for pk in object_ids}

    for usage in usages:
        asset = usage.asset
        try:
            url = service.resolve_asset_url(asset, viewer=viewer)
        except Exception:
            url = None

        entry = {
            'asset_id': str(asset.asset_id),
            'filename': asset.original_filename or '',
            'mime_type': asset.mime_type or '',
            'size_bytes': asset.size_bytes or 0,
            'url': url,
        }
        result[usage.object_id].setdefault(usage.role, []).append(entry)

    return result


def _build_assets_for_object(obj, roles, viewer=None):
    """Один объект — удобная обёртка для одиночной сериализации."""
    if obj is None or obj.pk is None:
        return {role: [] for role in roles}
    batch = _build_assets_batch([obj], roles, viewer=viewer)
    return batch.get(str(obj.pk), {role: [] for role in roles})


class AssetsSerializerMixin:
    """
    Подмешивается в ModelSerializer.

    Подкласс объявляет:
        asset_roles = ['course_cover']

    При одиночной сериализации делает один запрос к AssetUsage.
    При many=True (через ListSerializer) делает ОДИН батч-запрос на весь список.

    При записи (create/update) ищет поля вида <role>_asset_id / <role>_asset_ids
    и синкает привязки через BindingApi.
    """

    asset_roles: list = []

    def get_assets(self, obj):
        # Проверяем есть ли предвычисленный батч в контексте (many=True)
        batch = self.context.get('_assets_batch')
        if batch is not None:
            return batch.get(str(obj.pk), {role: [] for role in self.asset_roles})

        request = self.context.get('request')
        viewer = getattr(request, 'user', None) if request is not None else None
        return _build_assets_for_object(obj, self.asset_roles, viewer=viewer)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['assets'] = self.get_assets(instance)
        return ret

    def _sync_asset_fields(self, instance):
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

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        Переопределяем many_init чтобы при many=True предвычислить
        assets одним батч-запросом и положить в context.
        """
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {
            'child': child_serializer,
        }
        list_kwargs.update({
            key: value for key, value in kwargs.items()
            if key in ('allow_empty', 'max_length', 'min_length')
        })
        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(meta, 'list_serializer_class', AssetsListSerializer)
        return list_serializer_class(*args, **list_kwargs)


class AssetsListSerializer(__import__('rest_framework').serializers.ListSerializer):
    """
    ListSerializer который делает один батч-запрос для всего списка
    и кладёт результат в context каждого дочернего сериализатора.
    """

    def to_representation(self, data):
        child = self.child
        asset_roles = getattr(child, 'asset_roles', [])

        if asset_roles and hasattr(data, '__iter__'):
            objects = list(data)
            if objects:
                request = self.context.get('request')
                viewer = getattr(request, 'user', None) if request is not None else None
                batch = _build_assets_batch(objects, asset_roles, viewer=viewer)
                # Кладём батч в контекст дочернего сериализатора
                child.context['_assets_batch'] = batch

        return super().to_representation(data)
