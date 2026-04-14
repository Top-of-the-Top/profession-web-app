"""
Разрешение плейсхолдеров local://<n> в JSON-строке document и загрузка файлов в хранилище
(S3 при USE_S3), путь: courses/course_<course_id>/lessons/<lesson_id>/asset_<n>.<ext>
"""
import json
import re
import uuid
from typing import Any

from django.core.files.storage import default_storage

# Плейсхолдеры фронта course-builder: "url": "local://1"
LOCAL_PLACEHOLDER_RE = re.compile(r'local://(\d+)')


def _guess_extension(filename: str, asset_type: str) -> str:
    if filename and '.' in filename:
        return '.' + filename.rsplit('.', 1)[-1].lower()[:10]
    if '/' in (asset_type or ''):
        ext = asset_type.split('/')[-1].lower()
        if ext in ('jpeg', 'jpg', 'png', 'gif', 'webp', 'svg', 'pdf', 'mp4', 'webm'):
            return '.' + ('jpg' if ext == 'jpeg' else ext)
    if asset_type in ('image', 'photo'):
        return '.png'
    if asset_type == 'video':
        return '.mp4'
    return ''


def upload_lesson_asset_file(
    course_id: uuid.UUID,
    lesson_id: uuid.UUID,
    asset_id: int,
    asset_type: str,
    file_obj,
) -> str:
    name = getattr(file_obj, 'name', '') or ''
    ext = _guess_extension(name, asset_type)
    path = f'courses/course_{course_id}/lessons/{lesson_id}/asset_{asset_id}{ext}'
    saved_path = default_storage.save(path, file_obj)
    return default_storage.url(saved_path)


def _get_uploaded_file_for_asset(files, asset_id: int, asset_file_field: str) -> Any:
    if not files:
        return None
    if asset_file_field and asset_file_field in files:
        return files[asset_file_field]
    for key in (f'asset_{asset_id}', str(asset_id)):
        if key in files:
            return files[key]
    return None


def upload_numeric_assets(
    course_id: uuid.UUID,
    lesson_id: uuid.UUID,
    assets_meta: list,
    files,
) -> dict[int, str]:
    """Загружает файлы и возвращает карту asset_id (int) -> публичный URL."""
    id_to_url: dict[int, str] = {}
    for item in assets_meta:
        aid = int(item['asset_id'])
        asset_type = (item.get('asset_type') or '').strip()
        field_hint = (item.get('asset_file') or '').strip()
        f = _get_uploaded_file_for_asset(files, aid, field_hint)
        if f is None:
            expected = field_hint or f'asset_{aid}'
            raise ValueError(
                f'Файл для asset_id={aid} не найден. Ожидается поле FormData «{expected}».'
            )
        url = upload_lesson_asset_file(course_id, lesson_id, aid, asset_type, f)
        id_to_url[aid] = url
    return id_to_url


def substitute_local_placeholders(document_str: str, id_to_url: dict[int, str]) -> str:
    """Подставляет URL вместо local://n в готовой JSON-строке."""

    def repl(match: re.Match) -> str:
        n = int(match.group(1))
        if n not in id_to_url:
            raise ValueError(
                f'В document встречается local://{n}, но нет успешной загрузки для asset_id={n}.'
            )
        return id_to_url[n]

    if not id_to_url:
        return document_str
    return LOCAL_PLACEHOLDER_RE.sub(repl, document_str)


def resolve_lesson_document_string(
    course_id: uuid.UUID,
    lesson_id: uuid.UUID,
    document_str: str,
    assets_meta: list,
    files,
) -> str:
    """
    Принимает JSON-строку document как от фронта (с local://), загружает assets,
    возвращает JSON-строку с реальными URL (готова для сохранения в Lesson.document).
    """
    if not assets_meta:
        return document_str
    id_to_url = upload_numeric_assets(course_id, lesson_id, assets_meta, files)
    return substitute_local_placeholders(document_str, id_to_url)


def parse_content_value(raw: Any) -> dict | None:
    if raw is None or raw == '':
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    raise TypeError('content must be object or JSON string')
