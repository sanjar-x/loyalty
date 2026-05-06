#!/bin/sh
# Container entrypoint with mode dispatch.
#
# Single Docker image deploys to three Railway services that differ only
# in the SERVICE_MODE env var:
#
#   SERVICE_MODE=web       (default) — alembic upgrade head + uvicorn HTTP server
#   SERVICE_MODE=worker     — TaskIQ worker (consumes outbox tasks from RabbitMQ)
#   SERVICE_MODE=scheduler  — TaskIQ scheduler (cron triggers, run exactly ONE instance)
#
# Migration policy: ONLY the web service runs `alembic upgrade head`. Worker
# and scheduler skip migrations to avoid concurrent migration locks during
# multi-service deploy (Railway may start all three services simultaneously).
#
# REC-005 audit (2026-05-06) added worker + scheduler dispatch — previously
# only web mode existed, leaving outbox events stuck PENDING and scheduled
# tasks (relay cron, prune) never firing.

set -e

MODE="${SERVICE_MODE:-web}"

case "$MODE" in
    web)
        echo "[entrypoint] mode=web — applying database migrations + starting uvicorn"
        alembic upgrade head
        exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
        ;;
    worker)
        echo "[entrypoint] mode=worker — starting TaskIQ worker (consumes outbox tasks)"
        # --workers controls concurrency per process; multiple worker service
        # replicas can run safely (FOR UPDATE SKIP LOCKED on outbox_messages).
        exec taskiq worker src.bootstrap.worker:broker --workers "${TASKIQ_WORKER_CONCURRENCY:-2}"
        ;;
    scheduler)
        echo "[entrypoint] mode=scheduler — starting TaskIQ scheduler (cron dispatch)"
        # IMPORTANT: run exactly ONE scheduler replica (multiple instances
        # would dispatch each cron tick multiple times). Configure replicas=1
        # at the Railway service level.
        exec taskiq scheduler src.bootstrap.scheduler:scheduler
        ;;
    *)
        echo "[entrypoint] ERROR: unknown SERVICE_MODE='$MODE' (expected web|worker|scheduler)" >&2
        exit 1
        ;;
esac
