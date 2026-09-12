from typing import Protocol

import httpx

from app.core.schemas import LineReply


class ReplySender(Protocol):
    async def send(self, reply: LineReply) -> None: ...
    async def show_loading(self, user_id: str, seconds: int = 20) -> None: ...


class LineReplySender:
    def __init__(self, access_token: str, timeout_seconds: float = 10.0) -> None:
        self.reply_url = "https://api.line.me/v2/bot/message/reply"
        self.loading_url = "https://api.line.me/v2/bot/chat/loading/start"
        self.access_token = access_token
        self.timeout = timeout_seconds

    async def show_loading(self, user_id: str, seconds: int = 20) -> None:
        if not self.access_token or not user_id:
            return
        headers = {"Authorization": "Bearer " + self.access_token}
        payload = {"chatId": user_id, "loadingSeconds": min(max(seconds, 5), 60)}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(self.loading_url, headers=headers, json=payload)
        except Exception:
            # Loading indicator is a UX enhancement; non-fatal if it fails
            pass

    async def send(self, reply: LineReply) -> None:
        if not self.access_token:
            return
        headers = {"Authorization": "Bearer " + self.access_token}
        payload = {
            "replyToken": reply.reply_token,
            "messages": [{"type": "text", "text": reply.text[:5000]}],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.reply_url, headers=headers, json=payload)
            response.raise_for_status()
