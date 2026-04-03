FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev --no-editable

RUN chmod +x scripts/entrypoint.sh

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --no-create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["./scripts/entrypoint.sh"]
