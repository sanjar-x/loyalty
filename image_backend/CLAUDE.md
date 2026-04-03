# Image Backend — Loyality Project

**Component:** `image-backend` | **Vault tag:** `[project/loyality, image-backend]`

Image processing microservice. Part of a larger project — see `../CLAUDE.md` for project overview, cross-service architecture, and Knowledge Base vault rules.

When saving research/documents to the vault, use `component: image-backend` in frontmatter and include `image-backend` in tags.

## Commands

```bash
docker compose up -d       # Postgres, Redis, RabbitMQ, MinIO (shared with backend)
uv sync                    # Dependencies (uv, NOT pip)
uv run uvicorn main:app --reload --port 8001
uv run alembic upgrade head
```

## Architecture

Same Clean Architecture as main backend but single module (`storage`). Handles image upload, resize, thumbnail generation, WebP conversion.

### Stack
- FastAPI, Python 3.14, async
- Pillow for image processing
- aiobotocore for MinIO (S3-compatible)
- TaskIQ for background processing

### Image Processing Pipeline
1. `POST /api/v1/media/upload` → presigned URL + storageObjectId
2. Client uploads to MinIO via presigned URL
3. `POST /api/v1/media/{id}/confirm` → worker processes image
4. Worker creates variants: thumbnail (150x150), medium (600x600), large (1200x1200), WebP

### Endpoints
- `POST /api/v1/media/upload` — get presigned URL
- `POST /api/v1/media/{id}/confirm` — confirm upload, start processing
- `GET /api/v1/media/{id}` — metadata + variants
- `GET /api/v1/media/{id}/status` — SSE processing status
- `DELETE /api/v1/media/{id}` — delete
- `POST /api/v1/media/external` — import from external URL

### Auth
X-API-Key header (server-to-server). No user-facing auth.
