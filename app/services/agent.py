from typing import Protocol

import httpx

from app.core.schemas import AgentResult, Citation


class Agent(Protocol):
    async def answer(self, query: str, context: str, citations: list[Citation]) -> AgentResult: ...


class OllamaAgent:
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 45.0) -> None:
        self.url = f"{base_url.rstrip('/')}/api/chat"
        self.model = model
        self.timeout = timeout_seconds

    async def answer(self, query: str, context: str, citations: list[Citation]) -> AgentResult:
        prompt = self._build_prompt(query, context, citations)
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": "Answer using the supplied context. If it is insufficient, say so."},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.url, json=payload)
                response.raise_for_status()
                content = response.json().get("message", {}).get("content", "").strip()
            if not content:
                raise ValueError("Ollama returned an empty answer")
            return AgentResult(answer=content)
        except (httpx.HTTPError, ValueError) as exc:
            return AgentResult(
                answer="ระบบ AI ภายในเครื่องยังไม่พร้อมใช้งาน กรุณาตรวจสอบ Ollama แล้วลองใหม่อีกครั้ง",
                status="fallback",
                tool_calls=[f"ollama_error:{type(exc).__name__}"],
            )

    @staticmethod
    def _build_prompt(query: str, context: str, citations: list[Citation]) -> str:
        sources = "\n".join(f"- {citation.source}" for citation in citations)
        return f"Question:\n{query}\n\nContext:\n{context or '(no local context found)'}\n\nSources:\n{sources or '(none)'}"
