# syntax=docker/dockerfile:1.7
#
# apps/workers/image/storage — TaskIQ worker for image processing
# without ML. Lean image — installs Pillow + aiobotocore via backend,
# but NOT torch / transformers / timm / kornia (those live in the
# sibling ``apps/workers/image/rmbg``).

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

RUN uv sync --frozen --no-dev --package image-storage-worker

WORKDIR /workspace/apps/workers/image/storage
CMD ["python", "-m", "taskiq", "worker", "main:broker"]
