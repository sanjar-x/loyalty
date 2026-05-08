"""
Shared Pydantic base schemas.

Provides ``CamelModel``, a pre-configured ``BaseModel`` subclass that
automatically converts ``snake_case`` Python fields to ``camelCase``
in JSON serialization. All presentation-layer request/response schemas
inherit from this base.

Also provides :class:`MoneySchema` — the project-wide canonical wire
shape for any monetary value (``{ amount, currency }``). Introduced
in CAT-001 on the catalog SKU surface, promoted to the shared kernel
in CAT-018 so pricing (preview) and any future module use the
identical type instead of hand-rolled mirrors that drift over time.

Typical usage:
    from src.shared.schemas import CamelModel, MoneySchema

    class OrderResponse(CamelModel):
        order_id: uuid.UUID  # serialized as "orderId"
        total: MoneySchema
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Pydantic base with automatic snake_case-to-camelCase aliasing.

    Attributes:
        model_config: Enables population by Python field name while
            serializing to camelCase aliases for JSON consumers.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class MoneySchema(CamelModel):
    """Project-wide canonical wire shape for monetary values.

    ``amount`` is in the smallest currency unit (kopecks for RUB,
    fen for CNY, cents for USD — per ISO 4217 ``minor_unit``).
    ``currency`` is a 3-letter ISO 4217 code, uppercase. Lives in the
    shared kernel so every module's wire contract for money is
    identical (CAT-001 / CAT-018).
    """

    amount: int = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
