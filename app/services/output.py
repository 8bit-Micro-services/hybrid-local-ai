from typing import Protocol

import httpx

from app.core.schemas import LineReply


class ReplySender(Protocol):
    async def send(self, reply: LineReply) -> None: ...


class LineReplySender:
    def __init__(self, access_token: str, timeout_seconds: float = 10.0) -> None:
        self.url = "https://api.line.me/v2/bot/message/reply"
        self.access_token = access_token
        self.timeout = timeout_seconds

    async def send(self, reply: LineReply) -> None:
        if not self.access_token:
            return
        headers = {"Authorization": "Bearer " + self.access_token}
        payload = {
            "replyToken": reply.reply_token,
            "messages": [{"type": "text", "text": reply.text[:5000]}],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
