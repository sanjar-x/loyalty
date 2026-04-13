"""
Repository implementation for delivery quotes.

Persists DeliveryQuote VOs server-side for price integrity.
Quotes are created during rate calculation and looked up
when creating a shipment.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.domain.interfaces import IDeliveryQuoteRepository
from src.modules.logistics.domain.value_objects import (
    DeliveryQuote,
    DeliveryType,
    Money,
    ShippingRate,
)
from src.modules.logistics.infrastructure.models import DeliveryQuoteModel


class DeliveryQuoteRepository(IDeliveryQuoteRepository):
    """SQLAlchemy implementation of IDeliveryQuoteRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, quote: DeliveryQuote) -> DeliveryQuote:
        model = DeliveryQuoteModel(
            id=quote.id,
            provider_code=quote.rate.provider_code,
            service_code=quote.rate.service_code,
            service_name=quote.rate.service_name,
            delivery_type=quote.rate.delivery_type.value,
            total_cost_amount=quote.rate.total_cost.amount,
            total_cost_currency=quote.rate.total_cost.currency_code,
            base_cost_amount=quote.rate.base_cost.amount,
            base_cost_currency=quote.rate.base_cost.currency_code,
            insurance_cost_amount=(
                quote.rate.insurance_cost.amount if quote.rate.insurance_cost else None
            ),
            insurance_cost_currency=(
                quote.rate.insurance_cost.currency_code
                if quote.rate.insurance_cost
                else None
            ),
            delivery_days_min=quote.rate.delivery_days_min,
            delivery_days_max=quote.rate.delivery_days_max,
            provider_payload=quote.provider_payload,
            quoted_at=quote.quoted_at,
            expires_at=quote.expires_at,
            origin_json={},
            destination_json={},
            parcels_json=[],
        )
        self._session.add(model)
        return quote

    async def get_by_id(self, quote_id: uuid.UUID) -> DeliveryQuote | None:
        stmt = select(DeliveryQuoteModel).where(DeliveryQuoteModel.id == quote_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: DeliveryQuoteModel) -> DeliveryQuote:
        insurance_cost = None
        if model.insurance_cost_amount is not None:
            insurance_cost = Money(
                amount=model.insurance_cost_amount,
                currency_code=model.insurance_cost_currency or "RUB",
            )

        rate = ShippingRate(
            provider_code=model.provider_code,
            service_code=model.service_code,
            service_name=model.service_name,
            delivery_type=DeliveryType(model.delivery_type),
            total_cost=Money(
                amount=model.total_cost_amount,
                currency_code=model.total_cost_currency,
            ),
            base_cost=Money(
                amount=model.base_cost_amount,
                currency_code=model.base_cost_currency,
            ),
            insurance_cost=insurance_cost,
            delivery_days_min=model.delivery_days_min,
            delivery_days_max=model.delivery_days_max,
        )

        return DeliveryQuote(
            id=model.id,
            rate=rate,
            provider_payload=model.provider_payload,
            quoted_at=model.quoted_at,
            expires_at=model.expires_at,
        )
