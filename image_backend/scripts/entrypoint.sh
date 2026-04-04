#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting TaskIQ worker..."
taskiq worker src.bootstrap.worker:broker --max-async-tasks 4 &

echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
