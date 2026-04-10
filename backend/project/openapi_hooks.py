"""Постобработка схемы OpenAPI (drf-spectacular)."""

from django.conf import settings


def canonicalize_tags(result, generator, request, public):
    """
    Приводит теги операций к именам из SPECTACULAR_SETTINGS['TAGS'],
    чтобы не дублировались варианты вроде «landing» и «Landing».
    """
    spec = getattr(settings, 'SPECTACULAR_SETTINGS', {})
    mapping = {t['name'].lower(): t['name'] for t in spec.get('TAGS', [])}

    for path_item in result.get('paths', {}).values():
        for method, op in list(path_item.items()):
            if method.startswith('x-') or not isinstance(op, dict):
                continue
            tags = op.get('tags')
            if not tags:
                continue
            seen = set()
            new_tags = []
            for tag in tags:
                canon = mapping.get(tag.lower(), tag)
                if canon not in seen:
                    seen.add(canon)
                    new_tags.append(canon)
            op['tags'] = new_tags

    root_tags = result.get('tags')
    if isinstance(root_tags, list):
        seen_names = set()
        out = []
        for tag_obj in root_tags:
            if not isinstance(tag_obj, dict) or 'name' not in tag_obj:
                out.append(tag_obj)
                continue
            name = tag_obj['name']
            canon = mapping.get(name.lower(), name)
            if canon in seen_names:
                continue
            seen_names.add(canon)
            out.append({**tag_obj, 'name': canon})
        result['tags'] = out

    return result
