"""Read-only validator for ``PATCH /admin/.../products/{id}`` (C1.2).

Mirrors the validation in ``UpdateProductHandler`` without committing —
the admin UI uses it to render a "saving will…" preview pane before the
operator clicks Save:

* ``diff`` — list of every field that would actually change
  (currentValue ≠ newValue), so the panel can highlight the delta.
* ``warnings`` — heuristics that signal recompute fan-outs the
  operator should be aware of (supplier / brand / category change all
  invalidate per-SKU pricing inputs).
* ``validation_errors`` — same checks UpdateProductHandler runs, but
  without raising — surfaced as a list so the front-end can render
  inline form errors.

``ok=True`` iff ``validation_errors`` is empty. Warnings do NOT close
the gate; they're advisory.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import (
    IBrandRepository,
    ICategoryRepository,
    IProductRepository,
)
from src.modules.catalog.domain.value_objects import (
    validate_i18n_completeness,
)
from src.shared.interfaces.logger import ILogger


@dataclass(frozen=True)
class ValidateProductUpdateQuery:
    """Input mirrors ``UpdateProductCommand`` (subset that's previewable).

    Only fields explicitly provided by the caller (``_provided_fields``)
    are considered. Same convention as the real PATCH handler.
    """

    product_id: uuid.UUID
    title_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    slug: str | None = None
    brand_id: uuid.UUID | None = None
    primary_category_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    tags: list[str] | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class FieldDiff:
    """One row of the field-level diff returned to the UI."""

    field: str
    from_value: Any
    to_value: Any


@dataclass(frozen=True)
class ValidationWarning:
    """Heuristic advisory — does NOT close the validation gate."""

    code: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class ValidationError:
    """Same checks as ``UpdateProductHandler``, returned as data instead of raised."""

    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class ValidateProductUpdateResult:
    ok: bool
    diff: list[FieldDiff]
    warnings: list[ValidationWarning]
    validation_errors: list[ValidationError]


class ValidateProductUpdateHandler:
    """Compute diff + warnings + validation errors for a proposed PATCH.

    Read-only: never mutates the aggregate, never commits.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        brand_repo: IBrandRepository,
        category_repo: ICategoryRepository,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._brand_repo = brand_repo
        self._category_repo = category_repo
        self._logger = logger.bind(handler="ValidateProductUpdateHandler")

    async def handle(
        self, query: ValidateProductUpdateQuery
    ) -> ValidateProductUpdateResult:
        product = await self._product_repo.get_with_variants(query.product_id)
        if product is None:
            raise ProductNotFoundError(product_id=query.product_id)

        diff: list[FieldDiff] = []
        warnings: list[ValidationWarning] = []
        validation_errors: list[ValidationError] = []

        # --- Build diff for every provided field that actually changes ---
        for field_name in query._provided_fields:
            current = getattr(product, field_name, None)
            proposed = getattr(query, field_name, None)
            if isinstance(current, tuple):
                # ``Product.tags`` is exposed as a read-only tuple view.
                current = list(current)
            if current != proposed:
                diff.append(
                    FieldDiff(
                        field=field_name,
                        from_value=current,
                        to_value=proposed,
                    )
                )

        # --- Validation: title_i18n cannot become empty ---
        if "title_i18n" in query._provided_fields:
            if not query.title_i18n:
                validation_errors.append(
                    ValidationError(
                        code="TITLE_EMPTY",
                        message="title_i18n must contain at least one language entry",
                        field="title_i18n",
                    )
                )
            else:
                try:
                    validate_i18n_completeness(query.title_i18n, "title_i18n")
                except ValueError as exc:
                    validation_errors.append(
                        ValidationError(
                            code="TITLE_INCOMPLETE_I18N",
                            message=str(exc),
                            field="title_i18n",
                        )
                    )

        # --- Validation: brand_id required + must exist ---
        if "brand_id" in query._provided_fields:
            if query.brand_id is None:
                validation_errors.append(
                    ValidationError(
                        code="BRAND_ID_REQUIRED",
                        message="brand_id cannot be set to null",
                        field="brand_id",
                    )
                )
            else:
                brand = await self._brand_repo.get(query.brand_id)
                if brand is None:
                    validation_errors.append(
                        ValidationError(
                            code="BRAND_NOT_FOUND",
                            message=f"Brand {query.brand_id} does not exist",
                            field="brand_id",
                        )
                    )

        # --- Validation: primary_category_id required + must exist ---
        if "primary_category_id" in query._provided_fields:
            if query.primary_category_id is None:
                validation_errors.append(
                    ValidationError(
                        code="PRIMARY_CATEGORY_ID_REQUIRED",
                        message="primary_category_id cannot be set to null",
                        field="primary_category_id",
                    )
                )
            else:
                category = await self._category_repo.get(query.primary_category_id)
                if category is None:
                    validation_errors.append(
                        ValidationError(
                            code="CATEGORY_NOT_FOUND",
                            message=(
                                f"Category {query.primary_category_id} does not exist"
                            ),
                            field="primary_category_id",
                        )
                    )

        # --- Validation: slug uniqueness if changing ---
        if (
            query.slug is not None
            and query.slug != product.slug
            and await self._product_repo.check_slug_exists_excluding(
                query.slug, query.product_id
            )
        ):
            validation_errors.append(
                ValidationError(
                    code="SLUG_CONFLICT",
                    message=f"Slug '{query.slug}' is already taken",
                    field="slug",
                )
            )

        # --- Heuristic warnings: any change to a pricing input fans out
        # ADR-005 recompute across this product's active SKUs. ``count``
        # comes from the eager-loaded variants — no extra round-trip.
        active_sku_count = sum(
            1
            for v in product.variants
            if v.deleted_at is None
            for s in v.skus
            if s.deleted_at is None and s.is_active
        )

        def _changes(field_name: str) -> bool:
            if field_name not in query._provided_fields:
                return False
            return getattr(product, field_name) != getattr(query, field_name)

        if _changes("supplier_id") and active_sku_count:
            warnings.append(
                ValidationWarning(
                    code="SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE",
                    message=(
                        "Изменение поставщика сбросит SKU в PENDING и "
                        "запустит автономный пересчёт цен. До завершения "
                        "пересчёта эти SKU будут скрыты со storefront."
                    ),
                    details={"affected_sku_count": active_sku_count},
                )
            )

        if _changes("primary_category_id") and active_sku_count:
            warnings.append(
                ValidationWarning(
                    code="CATEGORY_CHANGE_TRIGGERS_RECOMPUTE",
                    message=(
                        "Изменение категории затронет category-scoped "
                        "переменные ценообразования и приведёт к "
                        "пересчёту цен SKU."
                    ),
                    details={"affected_sku_count": active_sku_count},
                )
            )

        if _changes("brand_id") and active_sku_count:
            warnings.append(
                ValidationWarning(
                    code="BRAND_CHANGE",
                    message=(
                        "Смена бренда не влияет на цены, но изменит "
                        "карточку товара на storefront — проверьте, что "
                        "новый бренд соответствует поставщику."
                    ),
                    details={"affected_sku_count": active_sku_count},
                )
            )

        return ValidateProductUpdateResult(
            ok=not validation_errors,
            diff=diff,
            warnings=warnings,
            validation_errors=validation_errors,
        )


__all__ = [
    "FieldDiff",
    "ValidateProductUpdateHandler",
    "ValidateProductUpdateQuery",
    "ValidateProductUpdateResult",
    "ValidationError",
    "ValidationWarning",
]
