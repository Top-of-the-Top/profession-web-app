import json
import tempfile
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from apps.courses.lesson_content import (
    resolve_lesson_document_string,
    substitute_local_placeholders,
    upload_numeric_assets,
)


class SubstituteLocalTest(SimpleTestCase):
    def test_replaces_local_placeholder(self):
        s = '{"url":"local://1","x":1}'
        out = substitute_local_placeholders(s, {1: 'https://cdn.example.com/a.png'})
        self.assertEqual(
            json.loads(out)['url'],
            'https://cdn.example.com/a.png',
        )

    def test_missing_placeholder_raises(self):
        with self.assertRaises(ValueError):
            substitute_local_placeholders('{"u":"local://2"}', {1: 'https://x'})


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class UploadNumericAssetsTest(SimpleTestCase):
    def test_upload_by_asset_file_field_name(self):
        course_id = uuid.uuid4()
        lesson_id = uuid.uuid4()
        f = SimpleUploadedFile('x.png', b'\x89PNG', content_type='image/png')
        files = {'asset_1': f}
        meta = [{'asset_id': 1, 'asset_type': 'image', 'asset_file': 'asset_1'}]
        m = upload_numeric_assets(course_id, lesson_id, meta, files)
        self.assertIn(1, m)
        self.assertTrue(m[1].startswith('http') or m[1].startswith('/media'))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ResolveLessonDocumentTest(SimpleTestCase):
    def test_end_to_end_local_string(self):
        course_id = uuid.uuid4()
        lesson_id = uuid.uuid4()
        doc = json.dumps(
            {
                'id': 'x',
                'blocks': [{'type': 'photo', 'url': 'local://1'}],
            },
            ensure_ascii=False,
        )
        f = SimpleUploadedFile('a.png', b'\x89PNG\r\n', content_type='image/png')
        files = {'asset_1': f}
        meta = [{'asset_id': 1, 'asset_type': 'image/png', 'asset_file': 'asset_1'}]
        out = resolve_lesson_document_string(course_id, lesson_id, doc, meta, files)
        self.assertNotIn('local://', out)
        self.assertIn('blocks', out)
