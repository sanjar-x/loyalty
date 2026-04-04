#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting TaskIQ worker in background..."
taskiq worker src.bootstrap.worker:broker --max-async-tasks 4 &

exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
