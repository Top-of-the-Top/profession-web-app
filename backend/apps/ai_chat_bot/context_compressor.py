from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence

from apps.ai_chat_bot.chat_types import ChatMessage

logger = logging.getLogger(__name__)

MAX_SUMMARY_CHARS = 500
SUMMARY_SENTENCES = 2


class BaseContextCompressor(ABC):
    """Сжимает батч сообщений чата в краткое текстовое резюме."""

    @abstractmethod
    def compress(self, current_summary: str, messages: Sequence[ChatMessage]) -> str:
        """
        Принимает текущее резюме и новый батч сообщений.
        Возвращает обновлённое резюме не длиннее MAX_SUMMARY_CHARS символов.
        """


class TextRankContextCompressor(BaseContextCompressor):
    """
    Извлекающая суммаризация на основе TextRank (sumy).

    Стратегия:
    - Сообщения пользователя сохраняются целиком — они короткие и содержат суть вопросов.
    - Ответы ассистента сжимаются через TextRank до SUMMARY_SENTENCES предложений.
    - Старое резюме объединяется с новым и обрезается до MAX_SUMMARY_CHARS.
    """

    def compress(self, current_summary: str, messages: Sequence[ChatMessage]) -> str:
        user_lines = [
            f"- {m.content}"
            for m in messages
            if m.role == "user" and m.content.strip()
        ]
        assistant_text = " ".join(
            m.content for m in messages if m.role == "assistant" and m.content.strip()
        )

        parts: list[str] = []

        if current_summary:
            parts.append(current_summary)

        if user_lines:
            parts.append("Студент спрашивал:\n" + "\n".join(user_lines))

        assistant_summary = self._summarize(assistant_text)
        if assistant_summary:
            parts.append("Ключевые объяснения:\n" + assistant_summary)

        combined = "\n\n".join(parts)
        return combined[:MAX_SUMMARY_CHARS]

    def _summarize(self, text: str) -> str:
        if not text.strip():
            return ""
        try:
            from sumy.nlp.tokenizers import Tokenizer
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.summarizers.text_rank import TextRankSummarizer

            parser = PlaintextParser.from_string(text, Tokenizer("russian"))
            summarizer = TextRankSummarizer()
            sentences = summarizer(parser.document, SUMMARY_SENTENCES)
            result = " ".join(str(s) for s in sentences)
            return result if result.strip() else text[:200]
        except Exception as exc:
            logger.warning("TextRank summarization failed, falling back to truncation: %s", exc)
            return text[:200]
