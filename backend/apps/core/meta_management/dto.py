from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PresignedUpload:
    method: str
    url: str
    storage_key: str
    expires_at: datetime
    fields: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectMeta:
    key: str
    size_bytes: int
    etag: str
    last_modified: datetime
    mime_type: str = ''


@dataclass(frozen=True)
class BuildStorageKeyResult:
    """Результат резервирования ключа: ключ + мета для сохранения в MediaAsset.storage_meta."""
    storage_key: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class StorageKeyHint:
    backend: str
    intent: str
    owner_id: str = ''
    filename: str = ''


@dataclass(frozen=True)
class UploadPolicy:
    backend: str
    max_size: int
    mime_allowlist: tuple
    default_visibility: str
    default_role: str


@dataclass(frozen=True)
class BindTarget:
    content_type_id: int
    object_id: str


@dataclass(frozen=True)
class InitiateResult:
    asset_id: str
    dedup: bool
    storage_backend: str
    upload: PresignedUpload = None
