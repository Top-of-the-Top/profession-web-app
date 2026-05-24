from collections import deque

from django.test import SimpleTestCase

from apps.ai_chat_bot.chat_types import ChatMessage
from apps.ai_chat_bot.context_builder import (
    COMPRESS_BATCH_SIZE,
    COMPRESSION_THRESHOLD,
    HISTORY_MAXLEN,
    ChatContextBuilder,
)


def _msg(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)


def _make_history(*pairs: tuple[str, str]) -> deque[ChatMessage]:
    """Создаёт deque из пар (role, content)."""
    d: deque[ChatMessage] = deque(maxlen=HISTORY_MAXLEN)
    for role, content in pairs:
        d.append(_msg(role, content))
    return d


class ChatContextBuilderTests(SimpleTestCase):

    def setUp(self):
        self.builder = ChatContextBuilder()

    # --- should_compress ---

    def test_should_not_compress_when_below_threshold(self):
        history = _make_history(*[("user", f"msg{i}") for i in range(COMPRESSION_THRESHOLD - 1)])
        self.assertFalse(self.builder.should_compress(history))

    def test_should_compress_at_threshold(self):
        history = _make_history(*[("user", f"msg{i}") for i in range(COMPRESSION_THRESHOLD)])
        self.assertTrue(self.builder.should_compress(history))

    def test_should_compress_above_threshold(self):
        history = _make_history(*[("user", f"msg{i}") for i in range(COMPRESSION_THRESHOLD + 2)])
        self.assertTrue(self.builder.should_compress(history))

    # --- extract_batch_for_compression ---

    def test_extract_batch_returns_correct_batch_size(self):
        history = _make_history(*[("user", f"msg{i}") for i in range(COMPRESSION_THRESHOLD)])
        batch, remaining = self.builder.extract_batch_for_compression(history)
        self.assertEqual(len(batch), COMPRESS_BATCH_SIZE)

    def test_extract_batch_remaining_has_correct_size(self):
        total = COMPRESSION_THRESHOLD
        history = _make_history(*[("user", f"msg{i}") for i in range(total)])
        batch, remaining = self.builder.extract_batch_for_compression(history)
        self.assertEqual(len(remaining), total - COMPRESS_BATCH_SIZE)

    def test_extract_batch_preserves_order(self):
        history = _make_history(*[("user", f"msg{i}") for i in range(COMPRESSION_THRESHOLD)])
        batch, remaining = self.builder.extract_batch_for_compression(history)
        self.assertEqual(batch[0].content, "msg0")
        self.assertEqual(list(remaining)[0].content, f"msg{COMPRESS_BATCH_SIZE}")

    def test_extract_batch_remaining_has_maxlen(self):
        history = _make_history(*[("user", f"msg{i}") for i in range(COMPRESSION_THRESHOLD)])
        _, remaining = self.builder.extract_batch_for_compression(history)
        self.assertEqual(remaining.maxlen, HISTORY_MAXLEN)

    # --- build_prompt_context ---

    def test_build_context_without_summary(self):
        history = _make_history(("user", "вопрос"), ("assistant", "ответ"))
        result = self.builder.build_prompt_context("", history)
        self.assertIn("user: вопрос", result)
        self.assertIn("assistant: ответ", result)
        self.assertNotIn("[Контекст", result)

    def test_build_context_with_summary_prepended(self):
        history = _make_history(("user", "новый вопрос"))
        result = self.builder.build_prompt_context("старый контекст", history)
        summary_pos = result.index("старый контекст")
        recent_pos = result.index("новый вопрос")
        self.assertLess(summary_pos, recent_pos)

    def test_build_context_empty_history_only_summary(self):
        result = self.builder.build_prompt_context("только резюме", deque(maxlen=HISTORY_MAXLEN))
        self.assertIn("только резюме", result)

    def test_build_context_both_empty_returns_empty(self):
        result = self.builder.build_prompt_context("", deque(maxlen=HISTORY_MAXLEN))
        self.assertEqual(result, "")

    # --- make_history ---

    def test_make_history_has_correct_maxlen(self):
        history = self.builder.make_history()
        self.assertEqual(history.maxlen, HISTORY_MAXLEN)
        self.assertEqual(len(history), 0)

    # --- load_history_from_messages ---

    def test_load_history_converts_orm_messages(self):
        class FakeMsg:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        msgs = [FakeMsg("user", "вопрос"), FakeMsg("assistant", "ответ")]
        history = self.builder.load_history_from_messages(msgs)
        self.assertEqual(len(history), 2)
        self.assertEqual(list(history)[0], ChatMessage(role="user", content="вопрос"))
        self.assertEqual(list(history)[1], ChatMessage(role="assistant", content="ответ"))

    def test_load_history_empty_list(self):
        history = self.builder.load_history_from_messages([])
        self.assertEqual(len(history), 0)
