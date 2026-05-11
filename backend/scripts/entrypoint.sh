#!/bin/sh
# Container entrypoint with mode dispatch.
#
# Single Docker image deploys to three Railway services that differ only
# in the SERVICE_MODE env var:
#
#   SERVICE_MODE=web              (default) — uvicorn HTTP server
#   SERVICE_MODE=worker            — TaskIQ worker (consumes outbox tasks from RabbitMQ)
#   SERVICE_MODE=image_ml_worker   — TaskIQ worker dedicated to Bria RMBG-2.0 (image_ml queue)
#   SERVICE_MODE=scheduler         — TaskIQ scheduler (cron triggers, run exactly ONE instance)
#
# Migration policy: managed exclusively via railway.toml preDeployCommand.
# See that file for the canonical alembic invocation. Migrations run in a
# fresh container BEFORE this entrypoint executes, so by the time we hit
# the dispatch below the schema is already at head. Do NOT add
# `alembic upgrade head` here — duplicate runners cause cross-service
# migration-lock contention (the original reason worker / scheduler skip).
#
# REC-005 audit (2026-05-06) added worker + scheduler dispatch — previously
# only web mode existed, leaving outbox events stuck PENDING and scheduled
# tasks (relay cron, prune) never firing.
#
# HARD-1 (2026-05-06) extracted alembic from this script to railway.toml's
# preDeployCommand for single-source-of-truth migration timing.

set -e

MODE="${SERVICE_MODE:-web}"

case "$MODE" in
    web)
        echo "[entrypoint] mode=web — starting uvicorn (migrations applied by Railway preDeployCommand)"
        exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
        ;;
    worker)
        echo "[entrypoint] mode=worker — starting TaskIQ worker (consumes outbox tasks)"
        # --workers controls concurrency per process; multiple worker service
        # replicas can run safely (FOR UPDATE SKIP LOCKED on outbox_messages).
        exec taskiq worker src.bootstrap.worker:broker --workers "${TASKIQ_WORKER_CONCURRENCY:-2}"
        ;;
    image_ml_worker)
        # IMG-007 — dedicated ML worker for the Bria RMBG-2.0 cutout pipeline.
        # The `remove_background` task registers ONLY when BG_REMOVAL_ENABLED=true
        # (conditional in src/modules/image/infrastructure/tasks.py), so this
        # service subscribes to the `image_ml` queue and no other worker does.
        # Concurrency stays at 1: the model is ~1.6 GB in RAM, parallel inference
        # would multiply that. Scale horizontally via replicas if throughput
        # becomes the bottleneck.
        echo "[entrypoint] mode=image_ml_worker — starting TaskIQ worker (Bria RMBG-2.0)"
        exec taskiq worker src.bootstrap.worker:broker --workers 1
        ;;
    scheduler)
        echo "[entrypoint] mode=scheduler — starting TaskIQ scheduler (cron dispatch)"
        # IMPORTANT: run exactly ONE scheduler replica (multiple instances
        # would dispatch each cron tick multiple times). Configure replicas=1
        # at the Railway service level.
        exec taskiq scheduler src.bootstrap.scheduler:scheduler
        ;;
    *)
        echo "[entrypoint] ERROR: unknown SERVICE_MODE='$MODE' (expected web|worker|image_ml_worker|scheduler)" >&2
        exit 1
        ;;
esac
