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
