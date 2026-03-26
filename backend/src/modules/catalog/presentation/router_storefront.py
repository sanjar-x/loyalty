"""
FastAPI router for storefront read-only endpoints.

Serves pre-processed attribute data for the frontend: filters, product
card attributes, comparison attributes, and product creation form.
All endpoints are public (no auth required) and read-only.
"""

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, Response, status

from src.modules.catalog.application.queries.storefront import (
    StorefrontCardAttributesHandler,
    StorefrontComparisonAttributesHandler,
    StorefrontFilterableAttributesHandler,
    StorefrontFormAttributesHandler,
)
from src.modules.catalog.presentation.schemas import (
    StorefrontCardResponse,
    StorefrontComparisonResponse,
    StorefrontFilterListResponse,
    StorefrontFormResponse,
)
from src.modules.identity.presentation.dependencies import RequirePermission


def _project_i18n(i18n_dict: dict[str, str], lang: str) -> str:
    """Project a single locale from an i18n dict with fallback chain."""
    if lang in i18n_dict:
        return i18n_dict[lang]
    # Fallback: first available locale
    if i18n_dict:
        return next(iter(i18n_dict.values()))
    return ""


storefront_router = APIRouter(
    prefix="/storefront/categories/{category_id}",
    tags=["Storefront"],
    route_class=DishkaRoute,
)


@storefront_router.get(
    path="/filters",
    status_code=status.HTTP_200_OK,
    response_model=StorefrontFilterListResponse,
    summary="Get filterable attributes for a category",
    description=(
        "Returns all attributes bound to this category where the effective "
        "is_filterable flag is True (with binding overrides applied). "
        "Dictionary attributes include their values with translations."
    ),
)
async def get_filterable_attributes(
    category_id: uuid.UUID,
    handler: FromDishka[StorefrontFilterableAttributesHandler],
    response: Response,
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Locale code for i18n projection (e.g. 'ru', 'en')",
    ),
) -> StorefrontFilterListResponse:
    result = await handler.handle(category_id)
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    data = StorefrontFilterListResponse.model_validate(result, from_attributes=True)
    if lang:
        for attr in data.attributes:
            attr.name = _project_i18n(attr.name_i18n, lang)
    return data


@storefront_router.get(
    path="/card-attributes",
    status_code=status.HTTP_200_OK,
    response_model=StorefrontCardResponse,
    summary="Get attributes for a product card (grouped)",
    description=(
        "Returns all attributes where the effective is_visible_on_card flag is True, "
        "grouped by attribute group and ordered by group sort_order then binding sort_order."
    ),
)
async def get_card_attributes(
    category_id: uuid.UUID,
    handler: FromDishka[StorefrontCardAttributesHandler],
    response: Response,
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Locale code for i18n projection (e.g. 'ru', 'en')",
    ),
) -> StorefrontCardResponse:
    result = await handler.handle(category_id)
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    data = StorefrontCardResponse.model_validate(result, from_attributes=True)
    if lang:
        for group in data.groups:
            for attr in group.attributes:
                attr.name = _project_i18n(attr.name_i18n, lang)
    return data


@storefront_router.get(
    path="/comparison-attributes",
    status_code=status.HTTP_200_OK,
    response_model=StorefrontComparisonResponse,
    summary="Get comparable attributes for a category",
    description=(
        "Returns all attributes where the effective is_comparable flag is True, "
        "ordered by binding sort_order."
    ),
)
async def get_comparison_attributes(
    category_id: uuid.UUID,
    handler: FromDishka[StorefrontComparisonAttributesHandler],
    response: Response,
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Locale code for i18n projection (e.g. 'ru', 'en')",
    ),
) -> StorefrontComparisonResponse:
    result = await handler.handle(category_id)
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    data = StorefrontComparisonResponse.model_validate(result, from_attributes=True)
    if lang:
        for attr in data.attributes:
            attr.name = _project_i18n(attr.name_i18n, lang)
    return data


@storefront_router.get(
    path="/form-attributes",
    status_code=status.HTTP_200_OK,
    response_model=StorefrontFormResponse,
    summary="Get attributes for product creation form",
    dependencies=[Depends(RequirePermission(codename="catalog:manage"))],
    description=(
        "Returns ALL attributes bound to this category, grouped by attribute group, "
        "with requirement levels, display types, validation rules, and all values "
        "for dictionary attributes. Used by the admin panel to render the product form."
    ),
)
async def get_form_attributes(
    category_id: uuid.UUID,
    handler: FromDishka[StorefrontFormAttributesHandler],
    response: Response,
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=5,
        description="Locale code for i18n projection (e.g. 'ru', 'en')",
    ),
) -> StorefrontFormResponse:
    result = await handler.handle(category_id)
    response.headers["Cache-Control"] = "private, max-age=300"
    data = StorefrontFormResponse.model_validate(result, from_attributes=True)
    if lang:
        for group in data.groups:
            for attr in group.attributes:
                attr.name = _project_i18n(attr.name_i18n, lang)
    return data
