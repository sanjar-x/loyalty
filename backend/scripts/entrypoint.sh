#!/bin/sh
# Container entrypoint with mode dispatch.
#
# Single Docker image deploys to three Railway services that differ only
# in the SERVICE_MODE env var:
#
#   SERVICE_MODE=web            (default) — uvicorn HTTP server
#   SERVICE_MODE=core_worker     — TaskIQ worker for all domains except media
#                                  (orders / payments / logistics / outbox / cron / etc)
#   SERVICE_MODE=media_worker    — TaskIQ worker for the media domain
#                                  (image_processing / image_maintenance / image_ml)
#   SERVICE_MODE=scheduler       — TaskIQ scheduler (cron triggers, run exactly ONE instance)
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
    core_worker)
        # Domain-split: the core worker subscribes to ALL queues EXCEPT the
        # image module's (which the dedicated ``media-worker`` service owns
        # exclusively via ``worker_media`` bootstrap). Zero queue overlap →
        # RabbitMQ delivers each task deterministically to the correct
        # service, no round-robin contention with the heavy media worker.
        echo "[entrypoint] mode=core_worker — starting TaskIQ worker (all domains except media)"
        # --workers controls concurrency per process; multiple core_worker
        # service replicas can run safely (FOR UPDATE SKIP LOCKED on
        # outbox_messages).
        exec taskiq worker src.bootstrap.worker_core:broker --workers "${TASKIQ_WORKER_CONCURRENCY:-2}"
        ;;
    media_worker)
        # Dedicated worker for the media domain (image processing variants,
        # maintenance cron, and Bria RMBG-2.0 background-removal ML). Uses
        # ``src.bootstrap.worker_media:broker`` which imports ONLY the
        # image module's task module — narrows the subscription to
        # ``image_processing`` / ``image_maintenance`` / ``image_ml``
        # queues. The core worker does NOT subscribe to these queues, so
        # no round-robin contention occurs.
        #
        # The ``remove_background`` task itself registers ONLY when
        # BG_REMOVAL_ENABLED=true (conditional in image/tasks.py), so even
        # if some future worker happened to import the image task module
        # without that flag it would NOT subscribe to ``image_ml``.
        #
        # Concurrency stays at 1: the Bria model is ~1.6 GB in RAM,
        # parallel inference would multiply that. Scale horizontally via
        # replicas if throughput becomes the bottleneck.
        echo "[entrypoint] mode=media_worker — starting TaskIQ worker (media domain + Bria RMBG-2.0)"
        exec taskiq worker src.bootstrap.worker_media:broker --workers 1
        ;;
    scheduler)
        echo "[entrypoint] mode=scheduler — starting TaskIQ scheduler (cron dispatch)"
        # IMPORTANT: run exactly ONE scheduler replica (multiple instances
        # would dispatch each cron tick multiple times). Configure replicas=1
        # at the Railway service level.
        exec taskiq scheduler src.bootstrap.scheduler:scheduler
        ;;
    *)
        echo "[entrypoint] ERROR: unknown SERVICE_MODE='$MODE' (expected web|core_worker|media_worker|scheduler)" >&2
        exit 1
        ;;
esac
