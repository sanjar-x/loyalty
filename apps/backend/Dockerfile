# syntax=docker/dockerfile:1.7
#
# apps/backend — FastAPI HTTP service.
#
# Standalone artefact: build context = THIS directory (``apps/backend/``),
# not the monorepo root. Railway service config sets Root Directory =
# ``apps/backend`` so the build can copy ``pyproject.toml uv.lock src/
# main.py …`` without reaching outside the directory. Local build:
#
#     docker build -t loyality-backend apps/backend
#
# ``apps/bot`` and ``apps/workers/scheduler`` still consume backend
# Python code via a path dependency (``backend = { path = "../backend" }``)
# and build from the monorepo root.

FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Resolution metadata + lockfile + README first so the layer cache
# survives any change that doesn't touch them. README is required by
# hatchling because ``pyproject.toml`` declares ``readme = "README.md"``.
COPY pyproject.toml uv.lock README.md ./

# Application code. Backend's installable package is ``src/`` (see
# ``[tool.hatch.build.targets.wheel] packages = ["src"]``). ``main.py``
# is the uvicorn entry point. ``alembic.ini`` + ``alembic/`` are needed
# at runtime by ``preDeployCommand`` (alembic upgrade head).
#
# ``seed/`` is intentionally NOT copied — it's developer tooling
# (``uv run python -m seed.main`` against a fresh local database) and
# ``apps/backend/.gitignore`` excludes it, so it isn't in the build
# context anyway.
COPY src/ ./src/
COPY main.py ./
COPY alembic.ini ./
COPY alembic/ ./alembic/

RUN uv sync --frozen --no-dev

EXPOSE 8080

# No CMD on purpose — the start command is owned by the Railway
# service config (``apps/backend/railway.toml`` for backend / web,
# Railway UI override for the core-worker service that shares this
# image). Keeping the start command out of the Dockerfile means one
# image can power multiple Railway services (web, core-worker) with
# different ``startCommand`` per service.
