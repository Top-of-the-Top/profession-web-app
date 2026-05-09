from django.test import SimpleTestCase

from apps.homeworks.services.errors import RequestValidationError


class RequestValidationErrorExtractTests(SimpleTestCase):
    def test_scalar_detail(self):
        err = RequestValidationError("Сообщение")
        self.assertEqual(err.message, "Сообщение")

    def test_nested_list_detail(self):
        err = RequestValidationError(["Внутри"])
        self.assertEqual(err.message, "Внутри")

    def test_dict_detail_first_field(self):
        err = RequestValidationError({"email": ["Некорректный формат."]})
        self.assertEqual(err.message, "Некорректный формат.")
