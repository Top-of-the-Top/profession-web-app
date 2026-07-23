import json
import re

ASSET_URI_RE = re.compile(
    r"asset://([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def extract_asset_ids(document_str):
    if not document_str:
        return []
    seen = set()
    result = []
    for match in ASSET_URI_RE.finditer(document_str):
        uid = match.group(1).lower()
        if uid in seen:
            continue
        seen.add(uid)
        result.append(uid)
    return result


def substitute_asset_uris(document_str, uri_to_url):
    if not document_str:
        return document_str

    def repl(match):
        key = match.group(1).lower()
        url = uri_to_url.get(key)
        if url is None:
            return match.group(0)
        return url

    return ASSET_URI_RE.sub(repl, document_str)


def parse_content_value(raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    raise TypeError("content must be object or JSON string")


_TEXT_BLOCK_TYPES = frozenset({
    "paragraph",
    "heading",
    "bulletListItem",
    "numberedListItem",
    "checkListItem",
    "quote",
    "codeBlock",
})


def _collect_inline_text(content_items: list) -> str:
    parts = []
    for item in content_items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
        elif item.get("type") == "link":
            parts.append(_collect_inline_text(item.get("content", [])))
    return "".join(parts)


def _extract_blocks(blocks: list, lines: list) -> None:
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") in _TEXT_BLOCK_TYPES:
            text = _collect_inline_text(block.get("content") or []).strip()
            if text:
                lines.append(text)
        children = block.get("children")
        if children:
            _extract_blocks(children, lines)


def extract_plain_text(document_str) -> str:
    if not document_str:
        return ""
    try:
        blocks = json.loads(document_str) if isinstance(document_str, str) else document_str
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(blocks, list):
        return ""
    lines: list[str] = []
    _extract_blocks(blocks, lines)
    return "\n".join(lines)
