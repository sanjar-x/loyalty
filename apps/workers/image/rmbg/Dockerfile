# syntax=docker/dockerfile:1.7
#
# apps/workers/image/rmbg — TaskIQ worker for Bria RMBG-2.0 background
# removal (queue ``image_rmbg_jobs``, routing key ``image.rmbg.remove``).
#
# Standalone artefact: build context = THIS directory, not the monorepo
# root. Railway service config sets Root Directory = ``apps/workers/image/rmbg``.
# Local build:
#
#     docker build -t loyality-image-rmbg-worker apps/workers/image/rmbg
#
# This is the only deployable that pulls in torch + transformers + timm
# + kornia (~2.5 GB resolved). The CPU-only torch wheel is pinned via
# the ``pytorch-cpu`` index in this directory's ``pyproject.toml``
# (REC-024 — Railway nodes are GPU-less).

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

# Heavy install — torch + transformers + timm + kornia. Layer cached
# as long as ``pyproject.toml`` / ``uv.lock`` are unchanged.
RUN uv sync --frozen --no-dev

# Application code. Flat layout — every Python module lives at the
# directory root next to ``main.py``.
COPY *.py ./

# No CMD on purpose — start command lives in
# ``apps/workers/image/rmbg/railway.toml`` so it can be tuned per
# environment without rebuilding the image.
