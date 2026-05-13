"""
ProductAttributeValue child entity (EAV pivot entity).

Links a product to a specific attribute dictionary value.
Not an aggregate root -- operations are managed through the
ProductAttributeValue repository and command handlers.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid

from attr import dataclass

from ._common import _generate_id


@dataclass
class ProductAttributeValue:
    """Product-level attribute assignment (EAV pivot entity).

    Links a product to a specific attribute dictionary value.
    This is a child entity -- not an aggregate root. It does not
    collect domain events; operations are managed through the
    ProductAttributeValue repository and command handlers.

    Attributes:
        id: Unique assignment identifier.
        product_id: FK to the parent Product aggregate.
        attribute_id: FK to the Attribute dictionary entry.
        attribute_value_id: FK to the specific AttributeValue chosen.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID

    @classmethod
    def create(
        cls,
        *,
        product_id: uuid.UUID,
        attribute_id: uuid.UUID,
        attribute_value_id: uuid.UUID,
        pav_id: uuid.UUID | None = None,
    ) -> ProductAttributeValue:
        """Factory method to construct a new ProductAttributeValue.

        Args:
            product_id: UUID of the parent Product.
            attribute_id: UUID of the Attribute being assigned.
            attribute_value_id: UUID of the chosen AttributeValue.
            pav_id: Optional pre-generated UUID; generates uuid4 if omitted.

        Returns:
            A new ProductAttributeValue instance.
        """
        return cls(
            id=pav_id or _generate_id(),
            product_id=product_id,
            attribute_id=attribute_id,
            attribute_value_id=attribute_value_id,
        )
