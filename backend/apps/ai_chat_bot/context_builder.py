from __future__ import annotations

import logging
from collections import deque

from apps.ai_chat_bot.chat_types import ChatMessage

logger = logging.getLogger(__name__)

COMPRESSION_THRESHOLD = 18  # при len(deque) >= этого значения — сжимаем
COMPRESS_BATCH_SIZE = 10    # сколько старых сообщений отдаём на сжатие
HISTORY_MAXLEN = 20         # максимальный размер deque


class ChatContextBuilder:
    """
    Отвечает за сборку контекста для запроса к AI и управление
    размером скользящего окна истории.

    Единственная ответственность — знать КАК собирать контекст.
    Не знает ничего о том, как сжимать (это дело BaseContextCompressor).
    """

    def should_compress(self, history: deque[ChatMessage]) -> bool:
        """Возвращает True, когда пора сжать старую часть истории."""
        return len(history) >= COMPRESSION_THRESHOLD

    def extract_batch_for_compression(
        self, history: deque[ChatMessage]
    ) -> tuple[list[ChatMessage], deque[ChatMessage]]:
        """
        Извлекает первые COMPRESS_BATCH_SIZE сообщений для сжатия.
        Возвращает (batch, оставшаяся_история).
        """
        messages = list(history)
        batch = messages[:COMPRESS_BATCH_SIZE]
        remaining: deque[ChatMessage] = deque(
            messages[COMPRESS_BATCH_SIZE:], maxlen=HISTORY_MAXLEN
        )
        return batch, remaining

    def build_prompt_context(
        self, summary: str, history: deque[ChatMessage]
    ) -> str:
        """
        Собирает строку контекста для передачи в AI:
        [резюме прошлого] + [последние сообщения].
        """
        parts: list[str] = []

        if summary:
            parts.append(f"[Контекст предыдущего разговора]\n{summary}")

        recent_lines = [m.to_prompt_line() for m in history]
        if recent_lines:
            parts.append("\n".join(recent_lines))

        return "\n\n".join(parts)

    def make_history(self) -> deque[ChatMessage]:
        """Фабричный метод для создания пустой истории с нужным maxlen."""
        return deque(maxlen=HISTORY_MAXLEN)

    def load_history_from_messages(
        self, messages: list
    ) -> deque[ChatMessage]:
        """
        Конвертирует список ORM-объектов Message в deque[ChatMessage].
        messages — список объектов с полями .role и .content.
        """
        history: deque[ChatMessage] = self.make_history()
        for msg in messages:
            history.append(ChatMessage(role=msg.role, content=msg.content))
        return history
