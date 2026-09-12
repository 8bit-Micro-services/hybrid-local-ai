import base64
import hashlib
import hmac
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.schemas import AgentResult
from app.main import create_app


class FakeAgent:
    def __init__(self):
        self.received_histories = []

    async def answer(self, query, context, citations, history=None):
        self.received_histories.append(history)
        return AgentResult(answer=f"ตอบ: {query}")

    async def ping(self):
        return True


class FakeSender:
    def __init__(self):
        self.replies = []
        self.loading_calls = []

    async def show_loading(self, user_id, seconds=20):
        self.loading_calls.append((user_id, seconds))

    async def send(self, reply):
        self.replies.append(reply)


def make_client(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    sender = FakeSender()
    from app.orchestrator import Orchestrator
    from app.services.retrieval import LocalVaultRetriever

    orchestrator = Orchestrator(LocalVaultRetriever(str(vault)), FakeAgent(), sender)
    settings = Settings(
        line_channel_secret="secret",
        allowed_line_user_ids="U123",
        obsidian_vault_path=str(vault),
    )
    return TestClient(create_app(settings=settings, orchestrator=orchestrator)), sender


def signed(body: bytes) -> str:
    return base64.b64encode(hmac.new(b"secret", body, hashlib.sha256).digest()).decode()


def test_webhook_validates_signature_and_delivers_reply(tmp_path):
    client, sender = make_client(tmp_path)
    body = b'{"events":[{"type":"message","replyToken":"token","source":{"userId":"U123"},"message":{"type":"text","text":"hello"}}]}'

    response = client.post("/line/webhook", content=body, headers={"X-Line-Signature": signed(body)})

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "handled": "1"}
    assert sender.replies[0].text == "ตอบ: hello\n\n(หมายเหตุ: ไม่พบเอกสารที่ตรงกันในคลังความรู้ภายในเครื่อง)"


def test_orchestrator_maintains_multi_turn_history(tmp_path):
    client, sender = make_client(tmp_path)
    body1 = b'{"events":[{"type":"message","replyToken":"token1","source":{"userId":"U123"},"message":{"type":"text","text":"msg1"}}]}'
    body2 = b'{"events":[{"type":"message","replyToken":"token2","source":{"userId":"U123"},"message":{"type":"text","text":"msg2"}}]}'

    client.post("/line/webhook", content=body1, headers={"X-Line-Signature": signed(body1)})
    client.post("/line/webhook", content=body2, headers={"X-Line-Signature": signed(body2)})

    agent = client.app.state.orchestrator.agent
    assert len(agent.received_histories) == 2
    assert agent.received_histories[0] == []
    assert agent.received_histories[1] == [
        {"role": "user", "content": "msg1"},
        {"role": "assistant", "content": "ตอบ: msg1"},
    ]


def test_webhook_rejects_invalid_signature(tmp_path):
    client, _ = make_client(tmp_path)
    body = b'{"events":[]}'

    response = client.post("/line/webhook", content=body, headers={"X-Line-Signature": "bad"})

    assert response.status_code == 401


def test_webhook_rejects_unknown_user(tmp_path):
    client, _ = make_client(tmp_path)
    body = b'{"events":[{"type":"message","replyToken":"token","source":{"userId":"UNAUTHORIZED"},"message":{"type":"text","text":"hello"}}]}'

    response = client.post("/line/webhook", content=body, headers={"X-Line-Signature": signed(body)})

    assert response.status_code == 403


def test_webhook_rejects_invalid_payload_shape(tmp_path):
    client, _ = make_client(tmp_path)
    body = b'{"events":{}}'

    response = client.post("/line/webhook", content=body, headers={"X-Line-Signature": signed(body)})

    assert response.status_code == 400


def test_webhook_rejects_text_event_without_reply_token(tmp_path):
    client, _ = make_client(tmp_path)
    body = b'{"events":[{"type":"message","source":{"userId":"U123"},"message":{"type":"text","text":"hello"}}]}'

    response = client.post("/line/webhook", content=body, headers={"X-Line-Signature": signed(body)})

    assert response.status_code == 400


def test_webhook_rejects_message_over_limit(tmp_path):
    client, _ = make_client(tmp_path)
    body = b'{"events":[{"type":"message","replyToken":"token","source":{"userId":"U123"},"message":{"type":"text","text":"hello"}}]}'
    client.app.state.settings.max_message_length = 3

    response = client.post("/line/webhook", content=body, headers={"X-Line-Signature": signed(body)})

    assert response.status_code == 413


def test_ready_endpoint_reports_status(tmp_path):
    client, _ = make_client(tmp_path)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "vault": True,
        "ollama": True,
    }
