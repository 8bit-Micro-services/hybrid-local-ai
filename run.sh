#!/usr/bin/env sh
set -eu

if [ -x .venv/bin/uvicorn ]; then
    exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
