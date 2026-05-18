"""E2E happy-path for ``POST /api/v1/orders/buy-now``.

Полный сценарий «нажать одну кнопку»: customer регистрируется, создаёт
recipient через `POST /recipients`, видит SKU из catalog'а и оформляет
заказ одним запросом. Идём через ASGI-transport (in-process), реальная
DB подключена через `db_session` fixture.

Фикстуры catalog-сторону seedят напрямую через ORM-session — это
осознанный shortcut: писать через admin-API потребует
``admin_client`` + ~20 эндпоинтов на создание Supplier/Brand/Category/
Product/Variant/SKU, что выходит за рамки e2e на Buy Now. Domain
remains exercised: handler читает реальные строки через
``CatalogSkuPriceReader``.

Покрытие:

* T-2.1 happy-path с `PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=true` (default
  prod-state) — Order сразу PAID, response `autoCaptured=true`,
  `GET /orders/{id}` возвращает статус "PAID".
* T-2.2 happy-path с `PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=false` —
  Order остаётся PENDING, `autoCaptured=false`, есть `clientSecret`.
* T-2.3 unknown recipient → 422 (ownership/missing — путь параллельный
  unknown SKU из существующего файла).
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.e2e

_BUY_NOW_URL = "/api/v1/orders/buy-now"
_RECIPIENTS_URL = "/api/v1/recipients"


# ---------------------------------------------------------------------------
# Geo + catalog seed (autouse) — covers Supplier FK on countries + RUB currency
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _seed_countries(db_session: AsyncSession) -> None:
    """Seed countries referenced by Supplier FK (CN for cross-border)."""
    await db_session.execute(
        text(
            """
            INSERT INTO countries (alpha2, alpha3, numeric) VALUES
                ('CN', 'CHN', '156'),
                ('RU', 'RUS', '643')
            ON CONFLICT (alpha2) DO NOTHING
            """
        )
    )
    await db_session.flush()


# ---------------------------------------------------------------------------
# Buy-Now-ready SKU fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def buy_now_sku(db_session: AsyncSession) -> dict:
    """Insert a complete catalog graph (Supplier → Brand → Category →
    Product → Variant → SKU) and return ids + price for the assertions.

    The SKU is in legacy pricing (`price=15000`, `selling_price=NULL`)
    so the ``CatalogSkuPriceReader`` fallback resolves it without
    needing the autonomous-recompute pipeline.
    """
    supplier_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    category_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    unique_suffix = uuid.uuid4().hex[:8]

    # Supplier (cross-border, China)
    await db_session.execute(
        text(
            """
            INSERT INTO suppliers (id, name, type, country_code, is_active, version)
            VALUES (:id, :name, 'CROSS_BORDER', 'CN', true, 1)
            """
        ),
        {"id": supplier_id, "name": f"e2e-supplier-{unique_suffix}"},
    )

    # Brand
    await db_session.execute(
        text(
            """
            INSERT INTO brands (id, name, slug, version)
            VALUES (:id, :name, :slug, 0)
            """
        ),
        {
            "id": brand_id,
            "name": f"e2e-brand-{unique_suffix}",
            "slug": f"e2e-brand-{unique_suffix}",
        },
    )

    # Category (root, no parent)
    await db_session.execute(
        text(
            """
            INSERT INTO categories
                (id, parent_id, full_slug, level, name_i18n, slug, sort_order)
            VALUES
                (:id, NULL, :full_slug, 0,
                 cast('{"ru": "Кроссовки"}' as jsonb),
                 :slug, 0)
            """
        ),
        {
            "id": category_id,
            "full_slug": f"e2e-cat-{unique_suffix}",
            "slug": f"e2e-cat-{unique_suffix}",
        },
    )

    # Product (DRAFT — buy-now reader doesn't filter by status)
    await db_session.execute(
        text(
            """
            INSERT INTO products
                (id, primary_category_id, brand_id, supplier_id, slug,
                 title_i18n, description_i18n, attributes, status,
                 is_visible, version)
            VALUES
                (:id, :cat, :brand, :supp, :slug,
                 cast('{"ru": "Кроссовки e2e"}' as jsonb),
                 cast('{}' as jsonb),
                 cast('{}' as jsonb),
                 'DRAFT', true, 1)
            """
        ),
        {
            "id": product_id,
            "cat": category_id,
            "brand": brand_id,
            "supp": supplier_id,
            "slug": f"e2e-product-{unique_suffix}",
        },
    )

    # ProductVariant
    await db_session.execute(
        text(
            """
            INSERT INTO product_variants
                (id, product_id, name_i18n, sort_order, default_currency, version)
            VALUES
                (:id, :product, cast('{"ru": "42"}' as jsonb), 0, 'RUB', 0)
            """
        ),
        {"id": variant_id, "product": product_id},
    )

    # SKU with legacy ``price`` only (selling_price NULL, status='legacy').
    # CatalogSkuPriceReader fallback returns price when selling_price IS NULL.
    sku_price = 15_000  # 150 RUB
    await db_session.execute(
        text(
            """
            INSERT INTO skus
                (id, product_id, variant_id, sku_code, variant_hash,
                 is_active, price, currency, pricing_status, version)
            VALUES
                (:id, :product, :variant, :code, :hash,
                 true, :price, 'RUB', 'legacy', 1)
            """
        ),
        {
            "id": sku_id,
            "product": product_id,
            "variant": variant_id,
            "code": f"E2E-SKU-{unique_suffix}",
            "hash": uuid.uuid4().hex,
            "price": sku_price,
        },
    )

    await db_session.flush()

    return {
        "sku_id": sku_id,
        "product_id": product_id,
        "variant_id": variant_id,
        "supplier_id": supplier_id,
        "price": sku_price,
        "currency": "RUB",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_RECIPIENT_PAYLOAD = {
    "fullNameRu": "Иванов Иван Иванович",
    "fullNameLat": "Ivanov Ivan Ivanovich",
    "phone": "+79108897762",
    "email": "ivan@example.com",
    "passportSerial": "1234",
    "passportNumber": "567890",
    "passportIssueDate": date(2015, 5, 22).isoformat(),
    "birthDate": date(1990, 1, 1).isoformat(),
    # Минфин-валидный 12-значный ИНН (тот же, что в test_buy_now_handler.py)
    "inn": "500100732272",
}


def _buy_now_body(
    *,
    sku_id: uuid.UUID,
    recipient_id: uuid.UUID,
    idempotency_key: str,
    quantity: int = 1,
    delivery_quote_id: uuid.UUID | None = None,
) -> dict:
    body = {
        "skuId": str(sku_id),
        "quantity": quantity,
        "recipientId": str(recipient_id),
        "pickupCarrier": "cdek",
        "pickupPointId": "MSK-1",
        "idempotencyKey": idempotency_key,
    }
    if delivery_quote_id is not None:
        body["deliveryQuoteId"] = str(delivery_quote_id)
    return body


async def _create_recipient(client: AsyncClient) -> uuid.UUID:
    resp = await client.post(_RECIPIENTS_URL, json=_RECIPIENT_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["recipientId"])


# ---------------------------------------------------------------------------
# T-2.1 happy-path with auto-capture (current prod default)
# ---------------------------------------------------------------------------


async def test_buy_now_happy_path_auto_captured(
    authenticated_client: AsyncClient,
    buy_now_sku: dict,
) -> None:
    """End-to-end: register → create recipient → POST /orders/buy-now.

    Под ``PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=true`` (default config)
    Order рождается уже PAID, response carries ``autoCaptured=true``,
    последующий GET по order_id возвращает статус "PAID".
    """
    recipient_id = await _create_recipient(authenticated_client)
    body = _buy_now_body(
        sku_id=buy_now_sku["sku_id"],
        recipient_id=recipient_id,
        idempotency_key=f"buy-now-e2e-happy-{uuid.uuid4().hex[:8]}",
        quantity=2,
    )

    resp = await authenticated_client.post(_BUY_NOW_URL, json=body)
    assert resp.status_code == 201, resp.text
    payload = resp.json()

    # Wire-contract: every field in CreateOrderResponse is present.
    order_id = uuid.UUID(payload["orderId"])
    assert uuid.UUID(payload["paymentIntentId"])
    assert payload["totalAmount"] == buy_now_sku["price"] * 2
    assert payload["currency"] == buy_now_sku["currency"]
    assert payload["autoCaptured"] is True

    # Order is queryable by the same identity and shows PAID status.
    detail_resp = await authenticated_client.get(f"/api/v1/orders/{order_id}")
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    # CustomerOrderSchema.rawStatus == OrderStatus.value
    assert detail["rawStatus"] == "paid"
    assert detail["totalAmount"] == buy_now_sku["price"] * 2
    assert len(detail["items"]) == 1
    item = detail["items"][0]
    assert item["skuId"] == str(buy_now_sku["sku_id"])
    assert item["quantity"] == 2
    assert item["unitPriceAmount"] == buy_now_sku["price"]


# ---------------------------------------------------------------------------
# T-2.2 happy-path without auto-capture
# ---------------------------------------------------------------------------


async def test_buy_now_happy_path_without_auto_capture(
    monkeypatch: pytest.MonkeyPatch,
    authenticated_client: AsyncClient,
    buy_now_sku: dict,
) -> None:
    """Когда ``PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=false`` Order остаётся
    PENDING, response carries ``autoCaptured=false`` и ``clientSecret``
    (для будущего PSP-redirect)."""
    from src.bootstrap import config as cfg

    monkeypatch.setattr(cfg.settings, "PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE", False)

    recipient_id = await _create_recipient(authenticated_client)
    body = _buy_now_body(
        sku_id=buy_now_sku["sku_id"],
        recipient_id=recipient_id,
        idempotency_key=f"buy-now-e2e-pending-{uuid.uuid4().hex[:8]}",
    )

    resp = await authenticated_client.post(_BUY_NOW_URL, json=body)
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["autoCaptured"] is False
    assert payload["clientSecret"] is not None

    detail_resp = await authenticated_client.get(f"/api/v1/orders/{payload['orderId']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["rawStatus"] == "pending"


# ---------------------------------------------------------------------------
# T-2.3 recipient ownership check (different identity)
# ---------------------------------------------------------------------------


async def test_buy_now_returns_503_when_disabled_via_flag(
    monkeypatch: pytest.MonkeyPatch,
    authenticated_client: AsyncClient,
    buy_now_sku: dict,
) -> None:
    """Q10 / Sprint 1.5 — kill-switch ``settings.BUY_NOW_ENABLED=False``
    превращает endpoint в 503 ``BUY_NOW_DISABLED`` без касания handler'а.

    Дополнительно проверяем, что cart-flow остаётся работающим
    (косвенно: POST на ``/orders`` без cart_id попадает в handler и
    возвращает 422/404, не 503). Это гарантирует точечную область
    флага — Buy Now only.
    """
    from src.bootstrap import config as cfg

    monkeypatch.setattr(cfg.settings, "BUY_NOW_ENABLED", False)

    recipient_id = await _create_recipient(authenticated_client)
    body = _buy_now_body(
        sku_id=buy_now_sku["sku_id"],
        recipient_id=recipient_id,
        idempotency_key=f"buy-now-e2e-disabled-{uuid.uuid4().hex[:8]}",
    )

    resp = await authenticated_client.post(_BUY_NOW_URL, json=body)
    assert resp.status_code == 503, resp.text
    payload = resp.json()
    assert payload["error"]["code"] == "BUY_NOW_DISABLED"

    # Sanity: cart-flow остаётся доступен — попадает в handler, не
    # рубится флагом, возвращает 4xx (snapshot не существует — это OK,
    # главное что НЕ 503/BUY_NOW_DISABLED).
    cart_resp = await authenticated_client.post(
        "/api/v1/orders",
        json={
            "cartId": str(uuid.uuid4()),
            "snapshotId": str(uuid.uuid4()),
            "idempotencyKey": f"cart-flow-not-blocked-{uuid.uuid4().hex[:8]}",
        },
    )
    assert cart_resp.status_code != 503
    if cart_resp.status_code >= 400:
        assert cart_resp.json()["error"]["code"] != "BUY_NOW_DISABLED"


async def test_buy_now_rejects_recipient_owned_by_other_customer(
    authenticated_client: AsyncClient,
    buy_now_sku: dict,
    db_session: AsyncSession,
) -> None:
    """Ownership check: customer cannot use someone else's recipient.

    Создаём recipient на customer'е A, дёргаем buy-now от лица того
    же ``authenticated_client`` (customer A), но подменяем
    ``recipient_id`` на UUID, принадлежащий другой identity (вписан
    напрямую в DB, чтобы не плодить второго ASGI-customer'а).
    """
    other_identity_id = uuid.uuid4()
    other_recipient_id = uuid.uuid4()

    # Provision the foreign identity row + matching recipient row
    # directly via SQL — handler reads only IRecipientLookup ⇒
    # identity row не обязательна по FK (RecipientModel.identity_id
    # — nullable=false но не FK на identities). На случай если FK
    # появится — добавляем identity row.
    await db_session.execute(
        text(
            """
            INSERT INTO identities (id, primary_auth_method, account_type, is_active)
            VALUES (:id, 'LOCAL', 'CUSTOMER', true)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": other_identity_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO recipients (
                id, identity_id, full_name_ru, full_name_lat,
                phone, email,
                passport_serial, passport_number, passport_issue_date,
                birth_date, inn,
                validation_status, validation_failed_reason, is_archived,
                version
            ) VALUES (
                :id, :identity, :full_ru, :full_lat,
                :phone, :email,
                :ps, :pn, :pid,
                :bd, :inn,
                'pending', NULL, false,
                0
            )
            """
        ),
        {
            "id": other_recipient_id,
            "identity": other_identity_id,
            "full_ru": "Чужой Получатель",
            "full_lat": "Foreign Recipient",
            "phone": _RECIPIENT_PAYLOAD["phone"],
            "email": "foreign@example.com",
            "ps": _RECIPIENT_PAYLOAD["passportSerial"],
            "pn": _RECIPIENT_PAYLOAD["passportNumber"],
            # asyncpg требует ``datetime.date`` для колонок DATE — JSON
            # сериализованный isoformat не катит. Используем
            # date.fromisoformat для конвертации обратно.
            "pid": date.fromisoformat(_RECIPIENT_PAYLOAD["passportIssueDate"]),
            "bd": date.fromisoformat(_RECIPIENT_PAYLOAD["birthDate"]),
            "inn": _RECIPIENT_PAYLOAD["inn"],
        },
    )
    await db_session.flush()

    body = _buy_now_body(
        sku_id=buy_now_sku["sku_id"],
        recipient_id=other_recipient_id,
        idempotency_key=f"buy-now-e2e-ownership-{uuid.uuid4().hex[:8]}",
    )

    resp = await authenticated_client.post(_BUY_NOW_URL, json=body)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "ORDER_RECIPIENT_OWNERSHIP_MISMATCH"
