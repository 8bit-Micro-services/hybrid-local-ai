# Hybrid Local AI Loop

Runnable first slice of the LINE -> local retrieval -> Ollama -> LINE workflow.

## Run locally without Docker

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health`
Readiness check: `GET http://localhost:8000/ready`

LINE webhook: `POST http://localhost:8000/line/webhook`

Expose the webhook with a tunnel such as Cloudflare Tunnel or ngrok. Set the
LINE channel secret, access token, and allowed user IDs in `.env`.

The current retriever is intentionally dependency-light lexical matching over
Markdown files in `data/vault`. The `LocalVaultRetriever` interface is the
replacement point for embeddings and a vector database. `OllamaAgent` calls
`/api/chat`; it returns a user-safe fallback when Ollama is unavailable.

## Run with Docker Compose

Docker Compose starts the API and a local Ollama service. The Ollama model
files are kept in the named `ollama` volume, while the vault is mounted
read-only from `data/vault`.

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec ollama ollama pull "${OLLAMA_MODEL:-gemma4-64k}"
curl http://localhost:8000/health
```

The API is available on port `8000` by default. Set `PORT` in `.env` to change
the host port. Compose sets the internal Ollama URL to
`http://ollama:11434` by default, independently of the local-run
`OLLAMA_BASE_URL` value in `.env`. To use an Ollama instance outside this
Compose project, set `COMPOSE_OLLAMA_BASE_URL` before starting the stack.

To stop the stack while preserving downloaded models:

```bash
docker compose down
```

Do not put real LINE credentials in the image or commit `.env`. The Compose
file reads them at runtime.

For a first-time LINE integration, expose port `8000` through a tunnel and set
the webhook URL to `/line/webhook`. The LINE channel secret, access token, and
allowed user IDs must be configured in `.env`.

## Verify

```bash
.venv/bin/pytest -q
```

The test suite covers signature verification, rate limiting, webhook validation,
retrieval ranking/error states, and LINE authorization headers.

For a Compose smoke check:

```bash
docker compose config
docker compose ps
```
