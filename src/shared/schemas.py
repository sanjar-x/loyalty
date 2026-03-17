"""
Shared Pydantic base schemas.

Provides ``CamelModel``, a pre-configured ``BaseModel`` subclass that
automatically converts ``snake_case`` Python fields to ``camelCase``
in JSON serialization. All presentation-layer request/response schemas
inherit from this base.

Typical usage:
    from src.shared.schemas import CamelModel

    class OrderResponse(CamelModel):
        order_id: uuid.UUID  # serialized as "orderId"
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Pydantic base with automatic snake_case-to-camelCase aliasing.

    Attributes:
        model_config: Enables population by Python field name while
            serializing to camelCase aliases for JSON consumers.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
