import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.ai_chat_bot.api.dto import ConnectedMessage, parse_ws_request


class WsRequestParseTests(SimpleTestCase):
    def test_parse_start_new_chat(self):
        req = parse_ws_request({"type": "start new chat"})
        self.assertEqual(req.message_type, "start new chat")

    def test_parse_send_message_normalizes_type_case(self):
        req = parse_ws_request(
            {
                "type": "SEND MESSAGE",
                "chat_id": str(uuid.uuid4()),
                "content": {"text": "  hello  "},
            }
        )
        self.assertEqual(req.message_type, "send message")
        self.assertEqual(req.text, "hello")

    def test_parse_delete_chat_and_get_history(self):
        cid = str(uuid.uuid4())
        d = parse_ws_request({"type": "delete chat", "chat_id": cid})
        self.assertEqual(d.message_type, "delete chat")
        self.assertEqual(d.chat_id, cid)

        h = parse_ws_request({"type": "get history", "chat_id": cid})
        self.assertEqual(h.message_type, "get history")

    def test_parse_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            parse_ws_request({"type": "unknown"})

    def test_connected_message_serializes_chats(self):
        aid = uuid.uuid4()
        ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
        chat = SimpleNamespace(chat_id=aid, title="Чат 1", updated_at=ts)
        payload = ConnectedMessage(chats=[chat]).to_dict()
        self.assertEqual(payload["type"], "connected")
        self.assertEqual(len(payload["content"]["chats"]), 1)
        row = payload["content"]["chats"][0]
        self.assertEqual(row["chat_id"], str(aid))
        self.assertEqual(row["title"], "Чат 1")
