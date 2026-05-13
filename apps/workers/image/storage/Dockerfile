# syntax=docker/dockerfile:1.7
#
# apps/workers/image/storage — TaskIQ worker for image processing
# (queue ``image_storage_jobs``, routing keys ``image.storage.process``
# + ``image.storage.cleanup_orphans``).
#
# Standalone artefact: build context = THIS directory, not the monorepo
# root. Railway service config sets Root Directory =
# ``apps/workers/image/storage``. Local build:
#
#     docker build -t loyality-image-storage-worker apps/workers/image/storage
#
# Lean image — installs Pillow + aiobotocore + asyncpg + redis, but NOT
# torch / transformers / timm / kornia (those live in the sibling
# ``apps/workers/image/rmbg``).

FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Resolution metadata + lockfile first so the layer cache survives any
# code-only change.
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

# Application code. Flat layout — every Python module lives at the
# directory root next to ``main.py``.
COPY *.py ./

CMD ["python", "-m", "taskiq", "worker", "main:broker"]
