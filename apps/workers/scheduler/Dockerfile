# syntax=docker/dockerfile:1.7
#
# apps/workers/scheduler — TaskIQ scheduler (cron). Same lean image
# class as the backend's core-worker (no torch / no Pillow). The cron
# loop only ``.kicker()``-s the periodic tasks declared on its broker
# (e.g. image_cleanup_orphans). Bodies run in the consumer workers.

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

RUN uv sync --frozen --no-dev --package scheduler-worker

WORKDIR /workspace/apps/workers/scheduler
CMD ["python", "-m", "taskiq", "scheduler", "main:scheduler"]
