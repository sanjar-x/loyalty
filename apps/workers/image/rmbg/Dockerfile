# syntax=docker/dockerfile:1.7
#
# apps/workers/image/rmbg — TaskIQ worker for Bria RMBG-2.0 background
# removal (image_rmbg_jobs queue, routing key image.rmbg.remove).
#
# This is the only app that pulls in torch + transformers + timm +
# kornia (~2.5 GB resolved). The lean ``apps/workers/image/storage``
# worker handles Pillow resize + S3 uploads without these dependencies.
#
# Torch CPU wheel is pinned via ``[tool.uv.sources]`` in the app's
# ``pyproject.toml`` (redirecting torch / torchvision to the
# ``pytorch-cpu`` index defined at the workspace root). Without this
# redirect uv would resolve the multi-GB CUDA build (~2.5 GB of
# ``nvidia-*`` packages) which is wasted on Railway's GPU-less nodes
# (REC-024 lesson).

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

# Heavy install — torch + transformers + timm + kornia are ~2.5 GB
# resolved. Layer cached as long as the lockfile and the app's
# pyproject don't change.
RUN uv sync --frozen --no-dev --package image-rmbg-worker

WORKDIR /workspace/apps/workers/image/rmbg
CMD ["python", "-m", "taskiq", "worker", "main:broker"]
