import base64
import hashlib
import hmac
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.schemas import AgentResult
from app.main import create_app


class FakeAgent:
    async def answer(self, query, context, citations):
        return AgentResult(answer=f"ตอบ: {query}")

    async def ping(self):
        return True


class FakeSender:
    def __init__(self):
        self.replies = []

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
    assert sender.replies[0].text == "ตอบ: hello\n\nหมายเหตุ: ไม่พบเอกสารที่ตรงกันในคลังความรู้ภายในเครื่อง"


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
