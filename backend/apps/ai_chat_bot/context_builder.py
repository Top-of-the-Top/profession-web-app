from __future__ import annotations

import logging
from collections import deque

from apps.ai_chat_bot.chat_types import ChatMessage

logger = logging.getLogger(__name__)

COMPRESSION_THRESHOLD = 18
COMPRESS_BATCH_SIZE = 10
HISTORY_MAXLEN = 20


class ChatContextBuilder:
    def should_compress(self, history: deque[ChatMessage]) -> bool:
        return len(history) >= COMPRESSION_THRESHOLD

    def extract_batch_for_compression(
        self, history: deque[ChatMessage]
    ) -> tuple[list[ChatMessage], deque[ChatMessage]]:
        messages = list(history)
        batch = messages[:COMPRESS_BATCH_SIZE]
        remaining: deque[ChatMessage] = deque(
            messages[COMPRESS_BATCH_SIZE:], maxlen=HISTORY_MAXLEN
        )
        return batch, remaining

    def build_prompt_context(self, summary: str, history: deque[ChatMessage]) -> str:
        parts: list[str] = []
        if summary:
            parts.append(f"[Контекст предыдущего разговора]\n{summary}")
        recent_lines = [m.to_prompt_line() for m in history]
        if recent_lines:
            parts.append("\n".join(recent_lines))
        return "\n\n".join(parts)

    def make_history(self) -> deque[ChatMessage]:
        return deque(maxlen=HISTORY_MAXLEN)

    def load_history_from_messages(self, messages: list) -> deque[ChatMessage]:
        history = self.make_history()
        for msg in messages:
            history.append(ChatMessage(role=msg.role, content=msg.content))
        return history
