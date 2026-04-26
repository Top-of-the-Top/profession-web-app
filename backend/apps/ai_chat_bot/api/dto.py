from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class WsRequest(ABC):
    @property
    @abstractmethod
    def message_type(self) -> str:
        raise NotImplementedError


class WsMessage(ABC):
    @property
    @abstractmethod
    def message_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def to_content(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.message_type,
            "chat_id": "",
            "content": self.to_content(),
        }


@dataclass
class ConnectedMessage(WsMessage):
    chats: list[Any]

    @property
    def message_type(self) -> str:
        return "connected"

    def to_content(self) -> dict[str, Any]:
        return {
            "chats": [
                {
                    "chat_id": str(chat.chat_id),
                    "title": chat.title,
                    "updated_at": chat.updated_at.isoformat(),
                }
                for chat in self.chats
            ]
        }


@dataclass
class ChatCreatedMessage(WsMessage):
    chat_id: str

    @property
    def message_type(self) -> str:
        return "chat created"

    def to_content(self) -> dict[str, Any]:
        return {}

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["chat_id"] = self.chat_id
        return payload


@dataclass
class ChatDeletedMessage(WsMessage):
    @property
    def message_type(self) -> str:
        return "chat deleted"

    def to_content(self) -> dict[str, Any]:
        return {}


@dataclass
class HistoryReceivedMessage(WsMessage):
    chat_id: str
    history: list[Any]

    @property
    def message_type(self) -> str:
        return "history received"

    def to_content(self) -> dict[str, Any]:
        return {
            "history": [
                {
                    "message_id": str(message.message_id),
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                }
                for message in self.history
            ]
        }

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["chat_id"] = self.chat_id
        return payload


@dataclass
class StartingAnswerMessage(WsMessage):
    chat_id: str

    @property
    def message_type(self) -> str:
        return "starting answer"

    def to_content(self) -> dict[str, Any]:
        return {}

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["chat_id"] = self.chat_id
        return payload


@dataclass
class StreamingResponseMessage(WsMessage):
    chat_id: str
    chunk: str

    @property
    def message_type(self) -> str:
        return "streaming response"

    def to_content(self) -> dict[str, Any]:
        return {"chunk": self.chunk}

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["chat_id"] = self.chat_id
        return payload


@dataclass
class FinishingAnswerMessage(WsMessage):
    chat_id: str

    @property
    def message_type(self) -> str:
        return "finishing answer"

    def to_content(self) -> dict[str, Any]:
        return {}
    
    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["chat_id"] = self.chat_id
        return payload


@dataclass
class ErrorMessage(WsMessage):
    message: str

    @property
    def message_type(self) -> str:
        return "error"

    def to_content(self) -> dict[str, Any]:
        return {"message": self.message}


@dataclass
class StartNewChatRequest(WsRequest):
    @property
    def message_type(self) -> str:
        return "start new chat"


@dataclass
class DeleteChatRequest(WsRequest):
    chat_id: str

    @property
    def message_type(self) -> str:
        return "delete chat"


@dataclass
class GetHistoryRequest(WsRequest):
    chat_id: str

    @property
    def message_type(self) -> str:
        return "get history"


@dataclass
class SendMessageRequest(WsRequest):
    chat_id: str
    content: dict[str, Any]

    @property
    def text(self) -> str:
        return str(self.content.get("text", "")).strip()

    @property
    def message_type(self) -> str:
        return "send message"

def parse_ws_request(payload: dict[str, Any]) -> WsRequest:
    message_type = str(payload.get("type", "")).strip().lower()
    chat_id = str(payload.get("chat_id", "")).strip()
    content = payload.get("content", {})
    
    if message_type == "start new chat":
        return StartNewChatRequest()
    if message_type == "delete chat":
        return DeleteChatRequest(chat_id=chat_id)
    if message_type == "get history":
        return GetHistoryRequest(chat_id=chat_id)
    if message_type == "send message":
        return SendMessageRequest(chat_id=chat_id, content=content)

    raise ValueError("Unsupported message type")
