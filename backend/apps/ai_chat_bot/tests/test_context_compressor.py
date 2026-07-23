from django.test import SimpleTestCase

from apps.ai_chat_bot.chat_types import ChatMessage
from apps.ai_chat_bot.context_compressor import (
    MAX_SUMMARY_CHARS,
    BaseContextCompressor,
    TextRankContextCompressor,
)


def _msg(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)


class TextRankContextCompressorTests(SimpleTestCase):

    def setUp(self):
        self.compressor = TextRankContextCompressor()

    def test_implements_base(self):
        self.assertIsInstance(self.compressor, BaseContextCompressor)

    def test_empty_messages_empty_summary_returns_empty(self):
        result = self.compressor.compress("", [])
        self.assertEqual(result, "")

    def test_user_messages_preserved_in_output(self):
        messages = [_msg("user", "Что такое рекурсия?")]
        result = self.compressor.compress("", messages)
        self.assertIn("рекурсия", result)

    def test_multiple_user_questions_all_present(self):
        messages = [
            _msg("user", "Вопрос про циклы"),
            _msg("assistant", "Циклы используются для повторения кода."),
            _msg("user", "Вопрос про функции"),
        ]
        result = self.compressor.compress("", messages)
        self.assertIn("циклы", result.lower())
        self.assertIn("функции", result.lower())

    def test_existing_summary_included_in_output(self):
        existing = "Ранее обсуждали списки Python."
        messages = [_msg("user", "Новый вопрос")]
        result = self.compressor.compress(existing, messages)
        self.assertIn("списки", result)
        self.assertIn("Новый вопрос", result)

    def test_result_does_not_exceed_max_chars(self):
        long_content = "очень длинный текст про программирование. " * 30
        messages = [
            _msg("user", long_content),
            _msg("assistant", long_content),
        ]
        result = self.compressor.compress("начальное резюме " * 10, messages)
        self.assertLessEqual(len(result), MAX_SUMMARY_CHARS)

    def test_empty_user_messages_skipped(self):
        messages = [_msg("user", "   "), _msg("user", "нормальный вопрос")]
        result = self.compressor.compress("", messages)
        self.assertIn("нормальный вопрос", result)
        self.assertNotIn("   ", result)

    def test_only_assistant_messages_produces_summary(self):
        messages = [
            _msg("assistant", "Функция — это именованный блок кода. Она принимает аргументы и возвращает результат. Функции помогают избежать дублирования кода.")
        ]
        result = self.compressor.compress("", messages)
        self.assertGreater(len(result), 0)

    def test_compress_is_deterministic(self):
        messages = [
            _msg("user", "Что такое полиморфизм?"),
            _msg("assistant", "Полиморфизм — способность объектов разных классов обрабатываться единообразно."),
        ]
        result1 = self.compressor.compress("", messages)
        result2 = self.compressor.compress("", messages)
        self.assertEqual(result1, result2)
