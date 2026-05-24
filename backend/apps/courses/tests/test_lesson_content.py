import json

from django.test import SimpleTestCase

from apps.courses.lesson_content import (
    extract_asset_ids,
    extract_plain_text,
    parse_content_value,
    substitute_asset_uris,
)


class ExtractAssetIdsTest(SimpleTestCase):

    def test_extracts_single_uuid(self):
        uid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        doc = json.dumps({"url": f"asset://{uid}"})
        self.assertEqual(extract_asset_ids(doc), [uid])

    def test_deduplicates(self):
        uid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        doc = f"asset://{uid} asset://{uid}"
        self.assertEqual(extract_asset_ids(doc), [uid])

    def test_empty_string_returns_empty(self):
        self.assertEqual(extract_asset_ids(""), [])

    def test_no_assets_returns_empty(self):
        self.assertEqual(extract_asset_ids('{"url": "https://example.com"}'), [])


class SubstituteAssetUrisTest(SimpleTestCase):

    def test_replaces_asset_uri(self):
        uid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        doc = f"asset://{uid}"
        out = substitute_asset_uris(doc, {uid: "https://cdn.example.com/a.png"})
        self.assertEqual(out, "https://cdn.example.com/a.png")

    def test_missing_uri_keeps_original(self):
        uid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        doc = f"asset://{uid}"
        out = substitute_asset_uris(doc, {})
        self.assertEqual(out, doc)

    def test_empty_string_returns_empty(self):
        self.assertEqual(substitute_asset_uris("", {}), "")


class ParseContentValueTest(SimpleTestCase):

    def test_none_returns_none(self):
        self.assertIsNone(parse_content_value(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_content_value(""))

    def test_dict_returns_dict(self):
        d = {"key": "value"}
        self.assertEqual(parse_content_value(d), d)

    def test_json_string_returns_dict(self):
        d = {"key": "value"}
        self.assertEqual(parse_content_value(json.dumps(d)), d)

    def test_invalid_type_raises(self):
        with self.assertRaises(TypeError):
            parse_content_value(123)


class ExtractPlainTextTest(SimpleTestCase):

    def _doc(self, *blocks):
        return json.dumps(list(blocks))

    def _paragraph(self, *texts):
        return {
            "type": "paragraph",
            "content": [{"type": "text", "text": t, "styles": {}} for t in texts],
            "children": [],
        }

    def _heading(self, text, level=1):
        return {
            "type": "heading",
            "props": {"level": level},
            "content": [{"type": "text", "text": text, "styles": {}}],
            "children": [],
        }

    def _image(self):
        return {
            "type": "image",
            "props": {"url": "https://cdn.example.com/img.png"},
            "content": "",
            "children": [],
        }

    def _bullet(self, text, children=None):
        return {
            "type": "bulletListItem",
            "content": [{"type": "text", "text": text, "styles": {}}],
            "children": children or [],
        }

    def test_empty_string_returns_empty(self):
        self.assertEqual(extract_plain_text(""), "")

    def test_none_returns_empty(self):
        self.assertEqual(extract_plain_text(None), "")

    def test_paragraph_extracts_text(self):
        doc = self._doc(self._paragraph("Hello world"))
        self.assertEqual(extract_plain_text(doc), "Hello world")

    def test_heading_extracts_text(self):
        doc = self._doc(self._heading("Заголовок"))
        self.assertEqual(extract_plain_text(doc), "Заголовок")

    def test_multiple_blocks_joined_by_newline(self):
        doc = self._doc(self._heading("H1"), self._paragraph("Para"))
        self.assertEqual(extract_plain_text(doc), "H1\nPara")

    def test_image_block_ignored(self):
        doc = self._doc(self._paragraph("Before"), self._image(), self._paragraph("After"))
        self.assertEqual(extract_plain_text(doc), "Before\nAfter")

    def test_nested_children_extracted(self):
        child = self._bullet("Вложенный")
        parent = self._bullet("Родитель", children=[child])
        doc = self._doc(parent)
        self.assertEqual(extract_plain_text(doc), "Родитель\nВложенный")

    def test_link_inline_content_extracted(self):
        block = {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Visit ", "styles": {}},
                {
                    "type": "link",
                    "href": "https://example.com",
                    "content": [{"type": "text", "text": "site", "styles": {}}],
                },
            ],
            "children": [],
        }
        doc = json.dumps([block])
        self.assertEqual(extract_plain_text(doc), "Visit site")

    def test_invalid_json_returns_empty(self):
        self.assertEqual(extract_plain_text("{not json"), "")

    def test_empty_paragraph_skipped(self):
        doc = self._doc(self._paragraph(""), self._paragraph("real"))
        self.assertEqual(extract_plain_text(doc), "real")

    def test_code_block_extracted(self):
        block = {
            "type": "codeBlock",
            "content": [{"type": "text", "text": "print('hello')", "styles": {}}],
            "children": [],
        }
        doc = json.dumps([block])
        self.assertEqual(extract_plain_text(doc), "print('hello')")

    def test_numbered_list_extracted(self):
        block = {
            "type": "numberedListItem",
            "content": [{"type": "text", "text": "Первый пункт", "styles": {}}],
            "children": [],
        }
        doc = json.dumps([block])
        self.assertEqual(extract_plain_text(doc), "Первый пункт")
