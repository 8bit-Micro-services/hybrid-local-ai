.PHONY: help dev test docker-up docker-down docker-logs pull-model

help:
	@echo "Hybrid Local AI - Available commands:"
	@echo "  make dev          - Start local development server with hot reload"
	@echo "  make test         - Run test suite with pytest"
	@echo "  make docker-up    - Build and start full stack (App + Ollama) in Docker"
	@echo "  make docker-down  - Stop all Docker containers"
	@echo "  make docker-logs  - View live logs of Docker services"
	@echo "  make pull-model   - Download configured Ollama model into Docker container"

dev:
	.venv/bin/uvicorn app.main:app --reload --port 8000

test:
	.venv/bin/pytest -v

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

pull-model:
	docker compose exec ollama ollama pull $${OLLAMA_MODEL:-gemma4-64k}
