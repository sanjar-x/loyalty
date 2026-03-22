"""
Internal webhook endpoints for AI-service callbacks.

These endpoints are NOT protected by user authentication — they are secured
by network policy (private VPC / internal ingress only). They allow the
AI processing service to report the outcome of a media processing job.
"""

import hmac
import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.bootstrap.config import settings
from src.modules.catalog.application.commands.complete_product_media import (
    CompleteProductMediaCommand,
    CompleteProductMediaHandler,
    FailProductMediaCommand,
    FailProductMediaHandler,
)
from src.modules.catalog.presentation.schemas import (
    MediaProcessingFailedRequest,
    MediaProcessingWebhookRequest,
    WebhookAckResponse,
)


async def _verify_internal_token(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
) -> None:
    expected = settings.INTERNAL_WEBHOOK_SECRET.get_secret_value()
    if not expected:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    if not hmac.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=403, detail="Forbidden")


internal_router = APIRouter(
    prefix="/internal/media",
    tags=["Internal — AI Service Webhooks"],
    route_class=DishkaRoute,
    dependencies=[Depends(_verify_internal_token)],
)


@internal_router.post(
    path="/{media_id}/processed",
    status_code=status.HTTP_200_OK,
    summary="AI processing completed",
    description="Callback from AI-service after successful media processing.",
    response_model=WebhookAckResponse,
)
async def media_processed_webhook(
    media_id: uuid.UUID,
    request: MediaProcessingWebhookRequest,
    handler: FromDishka[CompleteProductMediaHandler],
) -> WebhookAckResponse:
    """Callback from AI-service after successful media processing."""
    command = CompleteProductMediaCommand(
        media_id=media_id,
        object_key=request.object_key,
        content_type=request.content_type,
        size_bytes=request.size_bytes,
    )
    await handler.handle(command)
    return WebhookAckResponse()


@internal_router.post(
    path="/{media_id}/failed",
    status_code=status.HTTP_200_OK,
    summary="AI processing failed",
    description="Callback from AI-service when media processing fails.",
    response_model=WebhookAckResponse,
)
async def media_failed_webhook(
    media_id: uuid.UUID,
    request: MediaProcessingFailedRequest,
    handler: FromDishka[FailProductMediaHandler],
) -> WebhookAckResponse:
    """Callback from AI-service when processing fails."""
    command = FailProductMediaCommand(media_id=media_id, reason=request.error)
    await handler.handle(command)
    return WebhookAckResponse()
