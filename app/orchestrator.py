import asyncio
import logging
from collections import defaultdict, deque
from threading import Lock
from uuid import uuid4

from app.core.schemas import AgentResult, LineEvent, LineReply, RetrievalResult
from app.services.agent import Agent
from app.services.output import ReplySender
from app.services.retrieval import LocalVaultRetriever

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        retriever: LocalVaultRetriever,
        agent: Agent,
        sender: ReplySender,
        max_history_turns: int = 4,
    ) -> None:
        self.retriever = retriever
        self.agent = agent
        self.sender = sender
        self.max_history_turns = max_history_turns
        self._history: dict[str, deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=self.max_history_turns * 2)
        )
        self._lock = Lock()

    async def handle(self, event: LineEvent) -> str:
        request_id = str(uuid4())
        logger.info("request_started request_id=%s user_id=%s", request_id, event.user_id)

        # Trigger LINE loading animation in background for better UX
        asyncio.create_task(self.sender.show_loading(event.user_id, seconds=30))

        retrieval = self.retriever.retrieve(event.message_text)
        logger.info(
            "retrieval_completed request_id=%s status=%s matches=%d",
            request_id,
            retrieval.status,
            len(retrieval.sources),
        )

        with self._lock:
            user_history = list(self._history[event.user_id])

        agent_result = await self._answer(event.message_text, retrieval, user_history)
        text = self._format_answer(agent_result, retrieval)

        # Save successful turn into memory
        if agent_result.status == "completed":
            with self._lock:
                self._history[event.user_id].append({"role": "user", "content": event.message_text})
                self._history[event.user_id].append({"role": "assistant", "content": agent_result.answer})

        await self.sender.send(LineReply(reply_token=event.reply_token, text=text))
        logger.info(
            "request_completed request_id=%s user_id=%s status=%s",
            request_id,
            event.user_id,
            agent_result.status,
        )
        return request_id

    async def _answer(
        self,
        query: str,
        retrieval: RetrievalResult,
        history: list[dict[str, str]] | None = None,
    ) -> AgentResult:
        if retrieval.status == "error":
            return AgentResult(
                answer="ระบบค้นหาความรู้ภายในเครื่องขัดข้อง กรุณาลองใหม่อีกครั้ง",
                status="fallback",
            )
        return await self.agent.answer(query, retrieval.context, retrieval.citations, history=history)

    @staticmethod
    def _format_answer(result: AgentResult, retrieval: RetrievalResult) -> str:
        answer = result.answer.strip()
        if retrieval.status == "empty":
            answer += "\n\n(หมายเหตุ: ไม่พบเอกสารที่ตรงกันในคลังความรู้ภายในเครื่อง)"
        return answer
