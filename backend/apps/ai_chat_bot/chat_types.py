from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str

    def to_prompt_line(self) -> str:
        return f"{self.role}: {self.content}"
