import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from app.core.config import Settings, get_settings
from app.core.schemas import LineEvent
from app.core.security import RateLimiter, verify_line_signature
from app.orchestrator import Orchestrator
from app.services.agent import OllamaAgent
from app.services.output import LineReplySender
from app.services.retrieval import LocalVaultRetriever

logger = logging.getLogger("hybrid_local_ai")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app(
    settings: Settings | None = None,
    orchestrator: Orchestrator | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    orchestrator = orchestrator or Orchestrator(
        retriever=LocalVaultRetriever(settings.obsidian_vault_path),
        agent=OllamaAgent(settings.ollama_base_url, settings.ollama_model),
        sender=LineReplySender(settings.line_channel_access_token),
    )
    limiter = RateLimiter(settings.rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        vault_path = Path(settings.obsidian_vault_path)
        vault_path.mkdir(parents=True, exist_ok=True)
        doc_count = len(list(vault_path.rglob("*.md")))
        logger.info(
            "Starting Hybrid Local AI service | Ollama Model: %s | Vault: %s (%d docs) | Allowed users: %d",
            settings.ollama_model,
            settings.obsidian_vault_path,
            doc_count,
            len(settings.allowed_users),
        )
        if not settings.line_channel_secret or settings.line_channel_secret == "replace-me":
            logger.warning("LINE_CHANNEL_SECRET is not configured. Webhooks will be rejected.")
        yield
        logger.info("Shutting down Hybrid Local AI service")

    app = FastAPI(title="Hybrid Local AI Loop", version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.orchestrator = orchestrator

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict[str, str | bool]:
        vault_ready = orchestrator.retriever.vault_path.is_dir()
        ollama_ready = await orchestrator.agent.ping()
        status = "ready" if (vault_ready and ollama_ready) else "degraded"
        return {
            "status": status,
            "vault": vault_ready,
            "ollama": ollama_ready,
        }

    @app.post("/line/webhook")
    async def line_webhook(request: Request) -> dict[str, str]:
        body = await request.body()
        signature = request.headers.get("X-Line-Signature")
        if not verify_line_signature(body, signature, settings.line_channel_secret):
            raise HTTPException(status_code=401, detail="Invalid LINE signature")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise HTTPException(status_code=400, detail="Invalid LINE payload")

        handled = 0
        for raw_event in payload.get("events", []):
            if not isinstance(raw_event, dict):
                raise HTTPException(status_code=400, detail="Invalid LINE event")
            message = raw_event.get("message", {})
            if raw_event.get("type") != "message" or not isinstance(message, dict) or message.get("type") != "text":
                continue
            source = raw_event.get("source", {})
            if not isinstance(source, dict):
                raise HTTPException(status_code=400, detail="Invalid LINE source")
            user_id = source.get("userId", "")
            raw_text = message.get("text", "")
            if not isinstance(raw_text, str):
                raise HTTPException(status_code=400, detail="Invalid text event")
            text = raw_text.strip()
            if user_id not in settings.allowed_users:
                raise HTTPException(status_code=403, detail="User is not allowed")
            if not raw_event.get("replyToken") or not text:
                raise HTTPException(status_code=400, detail="Invalid text event")
            if len(text) > settings.max_message_length:
                raise HTTPException(status_code=413, detail="Message is too long")
            if not limiter.allow(user_id):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            timestamp = raw_event.get("timestamp")
            if timestamp is not None and (
                not isinstance(timestamp, (int, float)) or timestamp < 0
            ):
                raise HTTPException(status_code=400, detail="Invalid event timestamp")
            event = LineEvent(
                user_id=user_id,
                reply_token=raw_event["replyToken"],
                message_text=text,
                timestamp=datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc) if timestamp else None,
            )
            await orchestrator.handle(event)
            handled += 1

        return {"status": "ok", "handled": str(handled)}

    return app


app = create_app()
