import hashlib
import logging

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import AssetStatus, AssetUsage, MediaAsset
from .dto import StorageKeyHint, UploadPolicy
from .errors import (
    AssetBindConflict,
    AssetCommitMismatch,
    AssetIntentNotAllowed,
    AssetNotFound,
    AssetPolicyViolation,
    AssetStatusInvalid,
    AssetStorageUnavailable,
)
from .policies import get_bind_policy, get_intent_policy


logger = logging.getLogger(__name__)


class AssetService:

    def __init__(self, backends):
        self._backends = backends

    def get_backend(self, name):
        backend = self._backends.get(name)
        if backend is None:
            raise AssetStorageUnavailable(
                message=f'Backend {name} не зарегистрирован.',
                details={'backend': name},
            )
        return backend

    def _build_policy(self, intent_policy):
        return UploadPolicy(
            backend=intent_policy['backend'],
            max_size=intent_policy['max_size'],
            mime_allowlist=intent_policy['mime_allowlist'],
            default_visibility=intent_policy['default_visibility'],
            default_role=intent_policy['default_role'],
        )

    def create_pending_asset(self, owner, intent, filename, mime_type, size, sha256=''):
        intent_policy = get_intent_policy(intent)
        if intent_policy is None:
            raise AssetIntentNotAllowed(details={'intent': intent})

        if size <= 0 or size > intent_policy['max_size']:
            raise AssetPolicyViolation(
                message='Размер файла выходит за допустимые пределы.',
                details={'size': size, 'max_size': intent_policy['max_size']},
            )

        if intent_policy['mime_allowlist'] and mime_type not in intent_policy['mime_allowlist']:
            raise AssetPolicyViolation(
                message='MIME-тип не разрешён для данного назначения.',
                details={
                    'mime_type': mime_type,
                    'allowed': list(intent_policy['mime_allowlist']),
                },
            )

        backend_name = intent_policy['backend']
        backend = self.get_backend(backend_name)

        if sha256:
            existing = MediaAsset.objects.filter(
                owner=owner,
                checksum_sha256=sha256,
                storage_backend=backend_name,
                status=AssetStatus.READY,
            ).first()
            if existing is not None:
                return existing, True

        hint = StorageKeyHint(
            backend=backend_name,
            intent=intent,
            owner_id=str(owner.pk) if owner is not None else '',
            sha256=sha256,
            filename=filename,
        )
        storage_key = backend.build_storage_key(hint)

        asset = MediaAsset.objects.create(
            storage_backend=backend_name,
            storage_key=storage_key,
            original_filename=filename or '',
            mime_type=mime_type or '',
            size_bytes=size,
            checksum_sha256=sha256 or '',
            status=AssetStatus.PENDING,
            visibility=intent_policy['default_visibility'],
            owner=owner,
        )

        return asset, False

    def issue_upload_url(self, asset, intent):
        intent_policy = get_intent_policy(intent)
        if intent_policy is None:
            raise AssetIntentNotAllowed(details={'intent': intent})

        if intent_policy['backend'] != asset.storage_backend:
            raise AssetPolicyViolation(
                message='Intent не соответствует backend ассета.',
                details={
                    'intent': intent,
                    'intent_backend': intent_policy['backend'],
                    'asset_backend': asset.storage_backend,
                },
            )

        backend = self.get_backend(asset.storage_backend)
        policy = self._build_policy(intent_policy)
        return backend.issue_presigned_upload(asset.storage_key, policy)

    def commit_asset(self, asset_id):
        asset = self.get_asset(asset_id)

        if asset.status == AssetStatus.READY:
            return asset

        if asset.status != AssetStatus.PENDING:
            raise AssetStatusInvalid(
                details={'asset_id': str(asset.asset_id), 'status': asset.status},
            )

        backend = self.get_backend(asset.storage_backend)
        meta = backend.head(asset.storage_key)
        if meta is None:
            raise AssetCommitMismatch(
                message='Файл не найден в хранилище.',
                details={'storage_key': asset.storage_key},
            )

        if asset.size_bytes and meta.size_bytes != asset.size_bytes:
            raise AssetCommitMismatch(
                message='Размер загруженного файла не совпадает с заявленным.',
                details={'declared': asset.size_bytes, 'actual': meta.size_bytes},
            )

        sha = hashlib.sha256()
        for chunk in backend.stream_read(asset.storage_key):
            sha.update(chunk)
        computed_sha = sha.hexdigest()

        if asset.checksum_sha256 and computed_sha != asset.checksum_sha256:
            raise AssetCommitMismatch(
                message='SHA-256 не совпадает с заявленным.',
                details={'declared': asset.checksum_sha256, 'computed': computed_sha},
            )

        try:
            with transaction.atomic():
                asset.checksum_sha256 = computed_sha
                asset.size_bytes = meta.size_bytes
                if meta.mime_type:
                    asset.mime_type = meta.mime_type
                asset.status = AssetStatus.READY
                asset.committed_at = timezone.now()
                asset.save(update_fields=[
                    'checksum_sha256',
                    'size_bytes',
                    'mime_type',
                    'status',
                    'committed_at',
                ])
        except IntegrityError:
            existing = MediaAsset.objects.filter(
                owner=asset.owner,
                checksum_sha256=computed_sha,
                storage_backend=asset.storage_backend,
                status=AssetStatus.READY,
            ).exclude(pk=asset.pk).first()

            if existing is None:
                raise

            logger.info(
                'Dedup at commit: asset %s merged into existing %s',
                asset.asset_id,
                existing.asset_id,
            )

            asset.status = AssetStatus.DELETED
            asset.deleted_at = timezone.now()
            asset.save(update_fields=['status', 'deleted_at'])
            backend.delete(asset.storage_key)
            return existing

        return asset

    def register_server_asset(self, owner, intent, filename, mime_type, body):
        intent_policy = get_intent_policy(intent)
        if intent_policy is None:
            raise AssetIntentNotAllowed(details={'intent': intent})

        size = len(body)
        if size <= 0 or size > intent_policy['max_size']:
            raise AssetPolicyViolation(
                message='Размер файла выходит за допустимые пределы.',
                details={'size': size, 'max_size': intent_policy['max_size']},
            )

        if intent_policy['mime_allowlist'] and mime_type not in intent_policy['mime_allowlist']:
            raise AssetPolicyViolation(
                message='MIME-тип не разрешён для данного назначения.',
                details={
                    'mime_type': mime_type,
                    'allowed': list(intent_policy['mime_allowlist']),
                },
            )

        backend_name = intent_policy['backend']
        backend = self.get_backend(backend_name)

        sha = hashlib.sha256(body).hexdigest()

        hint = StorageKeyHint(
            backend=backend_name,
            intent=intent,
            owner_id=str(owner.pk) if owner is not None else '',
            sha256=sha,
            filename=filename,
        )
        storage_key = backend.build_storage_key(hint)

        backend.put_object(storage_key, body, mime_type=mime_type)

        asset = MediaAsset.objects.create(
            storage_backend=backend_name,
            storage_key=storage_key,
            original_filename=filename or '',
            mime_type=mime_type or '',
            size_bytes=size,
            checksum_sha256=sha,
            status=AssetStatus.READY,
            visibility=intent_policy['default_visibility'],
            owner=owner,
            committed_at=timezone.now(),
        )
        return asset

    def register_external_asset(self, owner, url, intent):
        intent_policy = get_intent_policy(intent)
        if intent_policy is None:
            raise AssetIntentNotAllowed(details={'intent': intent})

        asset = MediaAsset.objects.create(
            storage_backend='external',
            storage_key=url,
            original_filename='',
            mime_type='',
            size_bytes=0,
            checksum_sha256='',
            status=AssetStatus.READY,
            visibility=intent_policy['default_visibility'],
            owner=owner,
            committed_at=timezone.now(),
        )
        return asset

    def bind_asset(self, asset, content_object, role):
        if asset.status != AssetStatus.READY:
            raise AssetStatusInvalid(
                details={'asset_id': str(asset.asset_id), 'status': asset.status},
            )

        bind_policy = get_bind_policy(role)
        if bind_policy is None:
            raise AssetPolicyViolation(
                message='Неизвестная роль привязки.',
                details={'role': role},
            )

        if asset.storage_backend not in bind_policy['allowed_backends']:
            raise AssetPolicyViolation(
                message='Backend ассета не допускается для этой роли.',
                details={
                    'role': role,
                    'backend': asset.storage_backend,
                    'allowed': list(bind_policy['allowed_backends']),
                },
            )

        content_type = ContentType.objects.get_for_model(content_object)
        object_id = str(content_object.pk)

        max_usages = bind_policy['max_usages_per_target']
        if max_usages is not None:
            current = AssetUsage.objects.filter(
                content_type=content_type,
                object_id=object_id,
                role=role,
            ).count()
            if current >= max_usages:
                raise AssetPolicyViolation(
                    message='Превышен лимит привязок ассетов для этой сущности.',
                    details={'role': role, 'limit': max_usages},
                )

        try:
            with transaction.atomic():
                usage = AssetUsage.objects.create(
                    asset=asset,
                    content_type=content_type,
                    object_id=object_id,
                    role=role,
                )
        except IntegrityError:
            raise AssetBindConflict(
                details={
                    'asset_id': str(asset.asset_id),
                    'role': role,
                    'object_id': object_id,
                },
            )

        return usage

    def unbind_usage(self, usage):
        usage.delete()
        return None

    def resolve_asset_url(self, asset, viewer=None, ttl_seconds=300):
        if asset.status != AssetStatus.READY:
            raise AssetStatusInvalid(
                details={'asset_id': str(asset.asset_id), 'status': asset.status},
            )
        backend = self.get_backend(asset.storage_backend)
        return backend.resolve_url(asset, viewer=viewer, ttl_seconds=ttl_seconds)

    def get_asset(self, asset_id):
        try:
            return MediaAsset.objects.get(pk=asset_id)
        except MediaAsset.DoesNotExist:
            raise AssetNotFound(details={'asset_id': str(asset_id)})

    def get_asset_by_storage_key(self, storage_key, backend=None):
        qs = MediaAsset.objects.filter(storage_key=storage_key)
        if backend is not None:
            qs = qs.filter(storage_backend=backend)
        return qs.first()

    def get_usage(self, usage_id):
        try:
            return AssetUsage.objects.select_related('asset').get(pk=usage_id)
        except AssetUsage.DoesNotExist:
            raise AssetNotFound(
                message='Привязка не найдена.',
                details={'usage_id': str(usage_id)},
            )
