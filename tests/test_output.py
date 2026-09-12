import httpx
import pytest

from app.core.schemas import LineReply
from app.services.output import LineReplySender


class FakeResponse:
    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, **kwargs):
        self.headers = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, url, headers, json):
        self.headers = headers
        FakeClient.last_headers = headers
        return FakeResponse()


@pytest.mark.asyncio
async def test_line_sender_uses_bearer_token(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    await LineReplySender("token").send(LineReply(reply_token="reply", text="hello"))

    assert FakeClient.last_headers["Authorization"] == "Bearer token"
