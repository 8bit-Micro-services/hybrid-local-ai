from typing import Protocol

import httpx

from app.core.schemas import AgentResult, Citation


class Agent(Protocol):
    async def answer(
        self,
        query: str,
        context: str,
        citations: list[Citation],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResult: ...
    async def ping(self) -> bool: ...


class OllamaAgent:
    SYSTEM_PROMPT = (
        "คุณคือผู้ช่วย AI ส่วนบุคคลอัจฉริยะที่ทำงานบนเครื่อง Local อย่างปลอดภัยและเป็นส่วนตัว\n"
        "คำแนะนำในการตอบ:\n"
        "1. ตอบคำถามอย่างสุภาพ กระชับ ชัดเจน และตรงประเด็น โดยใช้ภาษาไทยเป็นหลัก (หรือตามภาษาที่ผู้ใช้ถาม)\n"
        "2. หากมีข้อมูลใน Context ให้ใช้ข้อมูลดังกล่าวในการตอบเป็นหลักอย่างถูกต้องตามข้อเท็จจริง\n"
        "3. หากไม่มีข้อมูลใน Context หรือข้อมูลไม่เพียงพอ ให้ตอบจากความรู้ทั่วไปอย่างระมัดระวัง พร้อมระบุให้ผู้ใช้ทราบอย่างสุภาพ\n"
        "4. จัดรูปแบบข้อความให้อ่านง่าย เช่น ใช้หัวข้อย่อยหรือ bullet points เมื่อเหมาะสม"
    )

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 45.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.url = f"{self.base_url}/api/chat"
        self.model = model
        self.timeout = timeout_seconds

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def answer(
        self,
        query: str,
        context: str,
        citations: list[Citation],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResult:
        messages: list[dict[str, str]] = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Append previous conversation history if available
        if history:
            messages.extend(history)

        user_content = self._build_user_message(query, context, citations)
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.model,
            "stream": False,
            "messages": messages,
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
                answer="ระบบ AI ภายในเครื่องยังไม่พร้อมใช้งาน กรุณาตรวจสอบว่า Ollama กำลังทำงานอยู่ แล้วลองใหม่อีกครั้ง",
                status="fallback",
                tool_calls=[f"ollama_error:{type(exc).__name__}"],
            )

    @staticmethod
    def _build_user_message(query: str, context: str, citations: list[Citation]) -> str:
        if not context:
            return f"คำถามของผู้ใช้:\n{query}"

        sources_summary = "\n".join(f"- {citation.source}" for citation in citations)
        return (
            f"คำถามของผู้ใช้:\n{query}\n\n"
            f"--- ข้อมูลอ้างอิงจากคลังความรู้ภายในเครื่อง (Context) ---\n"
            f"{context}\n\n"
            f"--- แหล่งที่มา (Sources) ---\n"
            f"{sources_summary or '(ไม่มี)'}"
        )
