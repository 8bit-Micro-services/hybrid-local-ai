import logging
from uuid import uuid4

from app.core.schemas import AgentResult, LineEvent, LineReply, RetrievalResult
from app.services.agent import Agent
from app.services.output import ReplySender
from app.services.retrieval import LocalVaultRetriever

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, retriever: LocalVaultRetriever, agent: Agent, sender: ReplySender) -> None:
        self.retriever = retriever
        self.agent = agent
        self.sender = sender

    async def handle(self, event: LineEvent) -> str:
        request_id = str(uuid4())
        logger.info("request_started request_id=%s user_id=%s", request_id, event.user_id)
        retrieval = self.retriever.retrieve(event.message_text)
        logger.info("retrieval_completed request_id=%s status=%s matches=%d", request_id, retrieval.status, len(retrieval.sources))
        agent_result = await self._answer(event.message_text, retrieval)
        text = self._format_answer(agent_result, retrieval)
        await self.sender.send(LineReply(reply_token=event.reply_token, text=text))
        logger.info("request_completed request_id=%s user_id=%s status=%s", request_id, event.user_id, agent_result.status)
        return request_id

    async def _answer(self, query: str, retrieval: RetrievalResult) -> AgentResult:
        if retrieval.status == "error":
            return AgentResult(
                answer="ระบบค้นหาความรู้ภายในเครื่องขัดข้อง กรุณาลองใหม่อีกครั้ง",
                status="fallback",
            )
        return await self.agent.answer(query, retrieval.context, retrieval.citations)

    @staticmethod
    def _format_answer(result: AgentResult, retrieval: RetrievalResult) -> str:
        answer = result.answer.strip()
        if retrieval.status == "empty":
            answer += "\n\nหมายเหตุ: ไม่พบเอกสารที่ตรงกันในคลังความรู้ภายในเครื่อง"
        return answer
