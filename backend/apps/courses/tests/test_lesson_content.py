import json

from django.test import SimpleTestCase

from apps.courses.lesson_content import (
    extract_asset_ids,
    substitute_asset_uris,
    parse_content_value,
)


class ExtractAssetIdsTest(SimpleTestCase):
    def test_extracts_single_uuid(self):
        uid = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        doc = json.dumps({'url': f'asset://{uid}'})
        self.assertEqual(extract_asset_ids(doc), [uid])

    def test_deduplicates(self):
        uid = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        doc = f'asset://{uid} asset://{uid}'
        self.assertEqual(extract_asset_ids(doc), [uid])

    def test_empty_string_returns_empty(self):
        self.assertEqual(extract_asset_ids(''), [])

    def test_no_assets_returns_empty(self):
        self.assertEqual(extract_asset_ids('{"url": "https://example.com"}'), [])


class SubstituteAssetUrisTest(SimpleTestCase):
    def test_replaces_asset_uri(self):
        uid = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        doc = f'asset://{uid}'
        out = substitute_asset_uris(doc, {uid: 'https://cdn.example.com/a.png'})
        self.assertEqual(out, 'https://cdn.example.com/a.png')

    def test_missing_uri_keeps_original(self):
        uid = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        doc = f'asset://{uid}'
        out = substitute_asset_uris(doc, {})
        self.assertEqual(out, doc)

    def test_empty_string_returns_empty(self):
        self.assertEqual(substitute_asset_uris('', {}), '')


class ParseContentValueTest(SimpleTestCase):
    def test_none_returns_none(self):
        self.assertIsNone(parse_content_value(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_content_value(''))

    def test_dict_returns_dict(self):
        d = {'key': 'value'}
        self.assertEqual(parse_content_value(d), d)

    def test_json_string_returns_dict(self):
        d = {'key': 'value'}
        self.assertEqual(parse_content_value(json.dumps(d)), d)

    def test_invalid_type_raises(self):
        with self.assertRaises(TypeError):
            parse_content_value(123)
