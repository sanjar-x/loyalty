# syntax=docker/dockerfile:1.7
#
# apps/workers/core — TaskIQ worker for non-image domain queues.
#
# Build context: monorepo root. ``uv sync --package core-worker``
# installs the backend graph WITHOUT torch / transformers / timm / kornia
# (those live in apps/workers/image/rmbg).

FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PATH="/workspace/.venv/bin:$PATH"

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY apps/ ./apps/

RUN uv sync --frozen --no-dev --package core-worker

CMD ["taskiq", "worker", "core_worker.worker:broker"]
