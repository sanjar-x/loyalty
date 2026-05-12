# syntax=docker/dockerfile:1.7
#
# apps/backend — FastAPI HTTP service + the library code consumed by every
# other app. This is BOTH a deployable artefact (the web service) and the
# ``loyality`` workspace member that ``apps/bot`` / ``apps/workers/*``
# depend on.
#
# Build context: monorepo root (``.``), NOT ``apps/backend``. The workspace
# lockfile and sibling apps live above this directory. Invoke from repo
# root via Railway's ``dockerfilePath = apps/backend/Dockerfile`` config
# or:
#
#     docker build -f apps/backend/Dockerfile -t loyality-backend .
#
# ``uv sync --package backend`` installs only this app's transitive
# graph — no torch / transformers / timm / kornia, those live in
# ``apps/workers/image/rmbg``.

FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PATH="/workspace/.venv/bin:$PATH"

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Workspace metadata + lockfile, plus every member's pyproject. uv needs
# to see every workspace member's manifest to resolve the lockfile; the
# install graph itself is narrowed by ``--package backend``.
COPY pyproject.toml uv.lock ./
COPY apps/ ./apps/

# Install only what the backend graph requires.
RUN uv sync --frozen --no-dev --package backend

EXPOSE 8080

# Run uvicorn via ``python -m`` so the interpreter prepends an empty
# string to ``sys.path`` (i.e. cwd is searched first). This is the
# canonical pattern for picking up a top-level ``main.py`` in the WORKDIR
# without packaging it as an installable module — appropriate because
# apps don't get imported from other code, only executed.
WORKDIR /workspace/apps/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
