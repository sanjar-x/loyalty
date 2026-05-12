"""
Shared E2E helper functions for catalog endpoint tests.

These are plain async functions (NOT pytest fixtures) that create prerequisite
entities via API calls.  Each helper generates unique slugs/codes using a UUID
suffix to avoid conflicts between tests.
"""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def create_brand(
    client: AsyncClient,
    *,
    name: str | None = None,
    slug: str | None = None,
    logo_url: str | None = None,
    **kwargs: object,
) -> dict:
    """POST /api/v1/catalog/brands -- create a brand and return response JSON."""
    suffix = uuid.uuid4().hex[:8]
    name = name or f"Test Brand {suffix}"
    slug = slug or f"brand-{suffix}"
    payload: dict = {"name": name, "slug": slug, **kwargs}
    if logo_url is not None:
        payload["logoUrl"] = logo_url
    resp = await client.post("/api/v1/catalog/brands", json=payload)
    assert resp.status_code == 201, (
        f"create_brand failed: {resp.status_code} {resp.text}"
    )
    return resp.json()


async def create_category(
    client: AsyncClient,
    *,
    name_i18n: dict[str, str] | None = None,
    slug: str | None = None,
    parent_id: str | None = None,
    template_id: str | None = None,
    **kwargs: object,
) -> dict:
    """POST /api/v1/catalog/categories -- create a category and return response JSON."""
    slug = slug or f"cat-{uuid.uuid4().hex[:8]}"
    name_i18n = name_i18n or {"ru": "Тест", "en": "Test"}
    payload: dict = {"nameI18N": name_i18n, "slug": slug, **kwargs}
    if parent_id is not None:
        payload["parentId"] = str(parent_id)
    if template_id is not None:
        payload["templateId"] = str(template_id)
    resp = await client.post("/api/v1/catalog/categories", json=payload)
    assert resp.status_code == 201, (
        f"create_category failed: {resp.status_code} {resp.text}"
    )
    return resp.json()


async def create_attribute(
    client: AsyncClient,
    *,
    code: str | None = None,
    slug: str | None = None,
    name_i18n: dict[str, str] | None = None,
    data_type: str = "string",
    ui_type: str = "dropdown",
    is_dictionary: bool = True,
    level: str = "product",
    is_filterable: bool = False,
    is_searchable: bool = False,
    is_comparable: bool = False,
    is_visible_on_card: bool = False,
    **kwargs: object,
) -> dict:
    """POST /api/v1/catalog/attributes -- create an attribute and return response JSON."""
    suffix = uuid.uuid4().hex[:8]
    code = code or f"attr_{suffix}"
    slug = slug or f"attr-{suffix}"
    name_i18n = name_i18n or {"ru": "Тест", "en": "Test"}
    payload: dict = {
        "code": code,
        "slug": slug,
        "nameI18N": name_i18n,
        "dataType": data_type,
        "uiType": ui_type,
        "isDictionary": is_dictionary,
        "level": level,
        "isFilterable": is_filterable,
        "isSearchable": is_searchable,
        "isComparable": is_comparable,
        "isVisibleOnCard": is_visible_on_card,
        **kwargs,
    }
    resp = await client.post("/api/v1/catalog/attributes", json=payload)
    assert resp.status_code == 201, (
        f"create_attribute failed: {resp.status_code} {resp.text}"
    )
    return resp.json()


async def create_attribute_value(
    client: AsyncClient,
    attribute_id: str,
    *,
    code: str | None = None,
    slug: str | None = None,
    value_i18n: dict[str, str] | None = None,
    **kwargs: object,
) -> dict:
    """POST /api/v1/catalog/attributes/{id}/values -- add a value and return response JSON."""
    suffix = uuid.uuid4().hex[:8]
    code = code or f"val_{suffix}"
    slug = slug or f"val-{suffix}"
    value_i18n = value_i18n or {"ru": "Значение", "en": "Value"}
    payload: dict = {
        "code": code,
        "slug": slug,
        "valueI18N": value_i18n,
        **kwargs,
    }
    resp = await client.post(
        f"/api/v1/catalog/attributes/{attribute_id}/values", json=payload
    )
    assert resp.status_code == 201, (
        f"create_attribute_value failed: {resp.status_code} {resp.text}"
    )
    return resp.json()


async def create_attribute_template(
    client: AsyncClient,
    *,
    code: str | None = None,
    name_i18n: dict[str, str] | None = None,
    **kwargs: object,
) -> dict:
    """POST /api/v1/catalog/attribute-templates -- create a template and return response JSON."""
    suffix = uuid.uuid4().hex[:8]
    code = code or f"tmpl_{suffix}"
    name_i18n = name_i18n or {"ru": "Шаблон", "en": "Template"}
    payload: dict = {"code": code, "nameI18N": name_i18n, **kwargs}
    resp = await client.post("/api/v1/catalog/attribute-templates", json=payload)
    assert resp.status_code == 201, (
        f"create_attribute_template failed: {resp.status_code} {resp.text}"
    )
    return resp.json()


async def bind_attribute_to_template(
    client: AsyncClient,
    template_id: str,
    attribute_id: str,
    *,
    requirement_level: str = "optional",
    **kwargs: object,
) -> dict:
    """POST /api/v1/catalog/attribute-templates/{tid}/attributes -- bind and return response JSON."""
    payload: dict = {
        "attributeId": str(attribute_id),
        "requirementLevel": requirement_level,
        **kwargs,
    }
    resp = await client.post(
        f"/api/v1/catalog/attribute-templates/{template_id}/attributes",
        json=payload,
    )
    assert resp.status_code == 201, (
        f"bind_attribute_to_template failed: {resp.status_code} {resp.text}"
    )
    return resp.json()
