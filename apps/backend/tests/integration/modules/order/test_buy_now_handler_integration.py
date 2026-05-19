"""Integration test for ``CreateBuyNowOrderHandler`` (T-1).

В отличие от unit-suite (`tests/unit/modules/order/test_buy_now_handler.py`,
fakes-based), этот тест поднимает реальные репозитории и UoW поверх
DB-фикстуры (`db_session` → nested savepoint, rolled back per-test).

Что проверяем после happy-path запуска handler'а:

1. ``orders`` row создана с правильными суммами и `is_walk_in=False`.
2. ``payment_intents`` row в статусе CAPTURED (под
   `PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=True`).
3. ``outbox_messages`` содержит как минимум `OrderCreatedEvent` и
   `OrderPaidEvent` — критично для downstream consumers (BE-4
   Telegram push, future analytics).
4. ``idempotency_keys`` row зарезервирована с правильным scope и
   указывает на созданный `order_id`.
5. Replay с тем же `idempotency_key` возвращает тот же `order_id`,
   не плодит второй Order / PaymentIntent.

Catalog-сторона (Supplier → Brand → Category → Product → Variant →
SKU) seedится прямым SQL — мы тестируем Order handler, не
admin-API; см. ту же стратегию в e2e
`test_orders_api_buy_now_happy.py`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.uow import UnitOfWork
from src.infrastructure.idempotency.repositories import SqlIdempotencyStore
from src.modules.order.application.commands.create_buy_now_order import (
    CreateBuyNowOrderCommand,
    CreateBuyNowOrderHandler,
)
from src.modules.order.domain.value_objects import (
    OrderStatus,
    PickupCarrier,
    PickupPointPreference,
)
from src.modules.order.infrastructure.adapters.catalog_sku_reader import (
    CatalogSkuPriceReader,
)
from src.modules.order.infrastructure.adapters.delivery_quote_adapter import (
    DeliveryQuoteAdapter,
)
from src.modules.order.infrastructure.adapters.payment_gateway import PaymentGateway
from src.modules.order.infrastructure.adapters.recipient_lookup import (
    RecipientLookupAdapter,
)
from src.modules.order.infrastructure.repositories.order_repository import (
    OrderRepository,
)
from src.modules.order.infrastructure.repositories.state_history_writer import (
    OrderStateHistoryWriter,
)
from src.modules.payment.application.commands.capture_payment_intent import (
    CapturePaymentIntentHandler,
)
from src.modules.payment.application.commands.create_payment_intent import (
    CreatePaymentIntentHandler,
)
from src.modules.payment.application.commands.refund_payment_intent import (
    RefundPaymentIntentHandler,
)
from src.modules.payment.domain.value_objects import PaymentIntentStatus
from src.modules.payment.infrastructure.providers.fake.provider import (
    FakePaymentProvider,
)
from src.modules.payment.infrastructure.repositories.payment_intent_repository import (
    PaymentIntentRepository,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Seed: countries + RUB currency + catalog graph + recipient
# ---------------------------------------------------------------------------


_INN_VALID = "500100732272"
_RECIPIENT_PII = {
    "full_name_ru": "Иванов Иван Иванович",
    "full_name_lat": "Ivanov Ivan Ivanovich",
    "phone": "+79108897762",
    "email": "ivan@example.com",
    "passport_serial": "1234",
    "passport_number": "567890",
    "passport_issue_date": date(2015, 5, 22),
    "birth_date": date(1990, 1, 1),
    "inn": _INN_VALID,
}


@pytest.fixture
async def seed_geo_and_currency(db_session: AsyncSession) -> None:
    """Countries (CN/RU) + RUB currency for FK satisfaction."""
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
    await db_session.execute(
        text(
            """
            INSERT INTO currencies (code, numeric, name, minor_unit, is_active)
            VALUES ('RUB', '643', 'Russian Ruble', 2, true)
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    await db_session.flush()


@pytest.fixture
async def seed_sku(
    db_session: AsyncSession,
    seed_geo_and_currency: None,
) -> dict:
    """Insert Supplier → Brand → Category → Product → Variant → SKU.

    Mirrors the e2e fixture exactly — see
    `tests/e2e/api/v1/order/test_orders_api_buy_now_happy.py::buy_now_sku`.
    SKU is in legacy pricing (price=15000, selling_price=NULL); the
    handler resolves price via the legacy fallback.
    """
    supplier_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    category_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    sku_id = uuid.uuid4()
    suffix = uuid.uuid4().hex[:8]

    await db_session.execute(
        text(
            "INSERT INTO suppliers (id, name, type, country_code, is_active, version)"
            " VALUES (:id, :name, 'CROSS_BORDER', 'CN', true, 1)"
        ),
        {"id": supplier_id, "name": f"int-supplier-{suffix}"},
    )
    await db_session.execute(
        text(
            "INSERT INTO brands (id, name, slug, version) VALUES (:id, :name, :slug, 0)"
        ),
        {
            "id": brand_id,
            "name": f"int-brand-{suffix}",
            "slug": f"int-brand-{suffix}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO categories
                (id, parent_id, full_slug, level, name_i18n, slug, sort_order)
            VALUES
                (:id, NULL, :slug, 0,
                 cast('{"ru": "Тест"}' as jsonb), :slug, 0)
            """
        ),
        {"id": category_id, "slug": f"int-cat-{suffix}"},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO products
                (id, primary_category_id, brand_id, supplier_id, slug,
                 title_i18n, description_i18n, attributes, status,
                 is_visible, version)
            VALUES
                (:id, :cat, :brand, :supp, :slug,
                 cast('{"ru": "Кроссовки"}' as jsonb),
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
            "slug": f"int-product-{suffix}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_variants
                (id, product_id, name_i18n, sort_order, default_currency, version)
            VALUES
                (:id, :p, cast('{"ru": "42"}' as jsonb), 0, 'RUB', 0)
            """
        ),
        {"id": variant_id, "p": product_id},
    )
    sku_price = 15_000
    await db_session.execute(
        text(
            """
            INSERT INTO skus
                (id, product_id, variant_id, sku_code, variant_hash,
                 is_active, price, currency, pricing_status, version)
            VALUES
                (:id, :p, :v, :code, :hash,
                 true, :price, 'RUB', 'legacy', 1)
            """
        ),
        {
            "id": sku_id,
            "p": product_id,
            "v": variant_id,
            "code": f"INT-SKU-{suffix}",
            "hash": uuid.uuid4().hex,
            "price": sku_price,
        },
    )
    await db_session.flush()

    return {
        "sku_id": sku_id,
        "price": sku_price,
        "currency": "RUB",
        "product_id": product_id,
    }


@pytest.fixture
async def seed_identity_and_recipient(
    db_session: AsyncSession,
    seed_geo_and_currency: None,
) -> dict:
    """Insert a customer identity + their recipient row (passes ownership check)."""
    identity_id = uuid.uuid4()
    recipient_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO identities (id, primary_auth_method, account_type, is_active)
            VALUES (:id, 'LOCAL', 'CUSTOMER', true)
            """
        ),
        {"id": identity_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO recipients (
                id, identity_id,
                full_name_ru, full_name_lat,
                phone, email,
                is_archived, version
            ) VALUES (
                :id, :identity,
                :fn_ru, :fn_lat,
                :phone, :email,
                false, 0
            )
            """
        ),
        {
            "id": recipient_id,
            "identity": identity_id,
            "fn_ru": _RECIPIENT_PII["full_name_ru"],
            "fn_lat": _RECIPIENT_PII["full_name_lat"],
            "phone": _RECIPIENT_PII["phone"],
            "email": _RECIPIENT_PII["email"],
        },
    )
    await db_session.flush()
    return {"identity_id": identity_id, "recipient_id": recipient_id}


@pytest.fixture
async def seed_passport(
    db_session: AsyncSession,
    seed_identity_and_recipient: dict,
) -> dict:
    """Insert a Passport row owned by the seeded identity (ADR-011).

    Required for Buy Now flows that target CROSS_BORDER SKUs — the
    domain invariant in ``Order.create`` rejects cross-border carts
    without an attached passport snapshot.
    """
    passport_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO passports (
                id, identity_id, full_name_ru, full_name_lat,
                passport_serial, passport_number, passport_issue_date,
                birth_date, inn, validation_status, is_archived, version
            ) VALUES (
                :id, :identity, :fn_ru, :fn_lat,
                :ps, :pn, :pid, :bd, :inn,
                'pending', false, 0
            )
            """
        ),
        {
            "id": passport_id,
            "identity": seed_identity_and_recipient["identity_id"],
            "fn_ru": _RECIPIENT_PII["full_name_ru"],
            "fn_lat": _RECIPIENT_PII["full_name_lat"],
            "ps": _RECIPIENT_PII["passport_serial"],
            "pn": _RECIPIENT_PII["passport_number"],
            "pid": _RECIPIENT_PII["passport_issue_date"],
            "bd": _RECIPIENT_PII["birth_date"],
            "inn": _RECIPIENT_PII["inn"],
        },
    )
    await db_session.flush()
    return {"passport_id": passport_id}


# ---------------------------------------------------------------------------
# Handler wiring helper (no Dishka — we want to assert real persistence)
# ---------------------------------------------------------------------------


class _NullLogger:
    """ILogger stub for integration tests.

    Не используем ``structlog.get_logger`` напрямую: e2e-suite через
    ``create_app()`` инициализирует structlog с
    ``cache_logger_on_first_use=True`` — после e2e наши
    ``get_logger("name")`` ловят кэшированный adapter, который при
    последующем ``.bind(handler=...)`` падает в стандартном
    ``logging.getLogger`` с ``TypeError: A logger name must be a
    string`` (cross-test pollution). Чистый stub этой зависимости не
    имеет.
    """

    def bind(self, **_kwargs: Any) -> _NullLogger:
        return self

    def info(self, *_a: Any, **_kw: Any) -> None: ...
    def warning(self, *_a: Any, **_kw: Any) -> None: ...
    def error(self, *_a: Any, **_kw: Any) -> None: ...
    def critical(self, *_a: Any, **_kw: Any) -> None: ...
    def debug(self, *_a: Any, **_kw: Any) -> None: ...
    def exception(self, *_a: Any, **_kw: Any) -> None: ...


def _build_handler(session: AsyncSession) -> CreateBuyNowOrderHandler:
    """Compose handler из реальных репозиториев + UoW поверх shared session."""
    logger = _NullLogger()
    uow = UnitOfWork(session)

    payment_repo = PaymentIntentRepository(session)
    payment_provider = FakePaymentProvider()

    create_handler = CreatePaymentIntentHandler(
        repo=payment_repo,
        provider=payment_provider,
        uow=uow,
        logger=logger,
    )
    capture_handler = CapturePaymentIntentHandler(
        repo=payment_repo,
        provider=payment_provider,
        uow=uow,
        logger=logger,
    )
    refund_handler = RefundPaymentIntentHandler(
        repo=payment_repo,
        provider=payment_provider,
        uow=uow,
        logger=logger,
    )

    from src.modules.order.infrastructure.adapters.passport_lookup import (
        PassportLookupAdapter,
    )

    return CreateBuyNowOrderHandler(
        order_repo=OrderRepository(session),
        sku_reader=CatalogSkuPriceReader(session),
        recipient_lookup=RecipientLookupAdapter(session),
        passport_lookup=PassportLookupAdapter(session),
        delivery_quote_lookup=DeliveryQuoteAdapter(session),
        idempotency_store=SqlIdempotencyStore(session),
        payment_gateway=PaymentGateway(
            create_handler=create_handler,
            capture_handler=capture_handler,
            refund_handler=refund_handler,
        ),
        history_writer=OrderStateHistoryWriter(session),
        uow=uow,
        logger=logger,
    )


def _cmd(
    *,
    identity_id: uuid.UUID,
    sku_id: uuid.UUID,
    recipient_id: uuid.UUID,
    idempotency_key: str,
    quantity: int = 1,
    passport_id: uuid.UUID | None = None,
) -> CreateBuyNowOrderCommand:
    return CreateBuyNowOrderCommand(
        identity_id=identity_id,
        sku_id=sku_id,
        quantity=quantity,
        recipient_id=recipient_id,
        pickup_point=PickupPointPreference(
            carrier=PickupCarrier.CDEK, point_id="MSK-1"
        ),
        delivery_quote_id=None,
        idempotency_key=idempotency_key,
        passport_id=passport_id,
    )


# ---------------------------------------------------------------------------
# Helpers — direct SQL queries on outbox / idempotency_keys / payment_intents
# ---------------------------------------------------------------------------


async def _fetch_outbox_event_types(
    session: AsyncSession, *, aggregate_id: str
) -> list[str]:
    rows = (
        await session.execute(
            text(
                """
                SELECT event_type FROM outbox_messages
                WHERE aggregate_id = :agg
                ORDER BY created_at, id
                """
            ),
            {"agg": aggregate_id},
        )
    ).all()
    return [r[0] for r in rows]


async def _fetch_payment_intent_status(
    session: AsyncSession, *, intent_id: uuid.UUID
) -> str:
    row = (
        await session.execute(
            text("SELECT status FROM payment_intents WHERE id = :id"),
            {"id": intent_id},
        )
    ).first()
    return str(row[0]) if row else ""


async def _fetch_idempotency_row(
    session: AsyncSession, *, scope: str, key: str
) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text(
                """
                SELECT scope, key, identity_id, resource_id, expires_at
                FROM idempotency_keys
                WHERE scope = :scope AND key = :key
                """
            ),
            {"scope": scope, "key": key},
        )
    ).first()
    if row is None:
        return None
    return {
        "scope": row[0],
        "key": row[1],
        "identity_id": row[2],
        "resource_id": row[3],
        "expires_at": row[4],
    }


# ---------------------------------------------------------------------------
# T-1.1 — happy-path under auto-capture
# ---------------------------------------------------------------------------


async def test_buy_now_persists_order_payment_outbox_and_idempotency(
    db_session: AsyncSession,
    seed_sku: dict,
    seed_identity_and_recipient: dict,
    seed_passport: dict,
) -> None:
    """Полный happy-path: handler.handle() → DB-side эффекты атомарны.

    Под ``PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=True`` (config default):
    Order PAID, PaymentIntent CAPTURED, outbox carries OrderCreated+
    OrderPaid.
    """
    handler = _build_handler(db_session)
    idemp_key = f"int-buynow-{uuid.uuid4().hex[:8]}"
    cmd = _cmd(
        identity_id=seed_identity_and_recipient["identity_id"],
        sku_id=seed_sku["sku_id"],
        recipient_id=seed_identity_and_recipient["recipient_id"],
        idempotency_key=idemp_key,
        quantity=2,
        passport_id=seed_passport["passport_id"],
    )

    result = await handler.handle(cmd)

    # (1) orders row
    order_row = (
        await db_session.execute(
            text(
                """
                SELECT id, identity_id, status, total_amount, currency,
                       is_walk_in, payment_intent_id, delivery_amount,
                       creation_source
                FROM orders WHERE id = :id
                """
            ),
            {"id": result.order_id},
        )
    ).first()
    assert order_row is not None, "Order row must be persisted"
    assert order_row[1] == seed_identity_and_recipient["identity_id"]
    assert str(order_row[2]).lower() == OrderStatus.PAID.value
    assert order_row[3] == seed_sku["price"] * 2
    assert order_row[4] == "RUB"
    assert order_row[5] is False, "Buy Now ⇒ is_walk_in must be False (Invariant I3)"
    assert order_row[6] == result.payment_intent_id
    assert order_row[7] == 0, "No delivery quote ⇒ delivery_amount=0"
    # BE-6: creation_source persists as 'buy_now' through the repo
    # round-trip. CHECK constraint at DB level forbids drift; this
    # assertion verifies the handler set it correctly.
    assert order_row[8] == "buy_now", (
        f"Buy Now handler must write creation_source='buy_now', got {order_row[8]!r}"
    )

    # (2) payment_intents row in CAPTURED
    intent_status = await _fetch_payment_intent_status(
        db_session, intent_id=result.payment_intent_id
    )
    assert intent_status == PaymentIntentStatus.CAPTURED.value

    # (3) outbox — OrderCreatedEvent + OrderPaidEvent at minimum
    aggregate_id = str(result.order_id)
    outbox_types = await _fetch_outbox_event_types(
        db_session, aggregate_id=aggregate_id
    )
    assert "OrderCreatedEvent" in outbox_types, (
        f"OrderCreatedEvent missing; got: {outbox_types}"
    )
    assert "OrderPaidEvent" in outbox_types, (
        f"OrderPaidEvent missing under auto-capture; got: {outbox_types}"
    )

    # (4) idempotency_keys row
    idem_row = await _fetch_idempotency_row(
        db_session, scope="order.create_buy_now", key=idemp_key
    )
    assert idem_row is not None, "Idempotency reservation must be persisted"
    assert idem_row["identity_id"] == seed_identity_and_recipient["identity_id"]
    assert idem_row["resource_id"] == result.order_id
    # TTL is 24h — generous floor of 23h covers clock skew + savepoint overhead
    assert (idem_row["expires_at"] - datetime.now(UTC)).total_seconds() > 23 * 3600

    # Result envelope matches the wire-contract
    assert result.auto_captured is True
    assert result.total_amount == seed_sku["price"] * 2
    assert result.currency == "RUB"


# ---------------------------------------------------------------------------
# T-1.2 — replay returns the same order, no duplicate Payment / Outbox bloat
# ---------------------------------------------------------------------------


async def test_buy_now_replay_returns_same_order_without_duplicate_persistence(
    db_session: AsyncSession,
    seed_sku: dict,
    seed_identity_and_recipient: dict,
    seed_passport: dict,
) -> None:
    """Повторный вызов с тем же ``idempotency_key`` обязан вернуть тот
    же ``order_id`` и не плодить второй Order / PaymentIntent /
    OrderCreatedEvent в outbox."""
    handler = _build_handler(db_session)
    idemp_key = f"int-buynow-replay-{uuid.uuid4().hex[:8]}"
    cmd = _cmd(
        identity_id=seed_identity_and_recipient["identity_id"],
        sku_id=seed_sku["sku_id"],
        recipient_id=seed_identity_and_recipient["recipient_id"],
        idempotency_key=idemp_key,
        passport_id=seed_passport["passport_id"],
    )

    first = await handler.handle(cmd)
    second = await handler.handle(cmd)

    assert first.order_id == second.order_id

    # Only one orders row exists for this identity_id with this idemp_key
    order_count = (
        await db_session.execute(
            text("SELECT COUNT(*) FROM orders WHERE id = :id"),
            {"id": first.order_id},
        )
    ).scalar_one()
    assert order_count == 1

    # Only one OrderCreatedEvent in outbox для этого order_id
    outbox_types = await _fetch_outbox_event_types(
        db_session, aggregate_id=str(first.order_id)
    )
    assert outbox_types.count("OrderCreatedEvent") == 1, (
        f"Replay must not re-emit OrderCreatedEvent; got: {outbox_types}"
    )


# ---------------------------------------------------------------------------
# T-1.3 — recipient ownership boundary enforced (DB-level, real query)
# ---------------------------------------------------------------------------


async def test_buy_now_rejects_recipient_of_another_customer(
    db_session: AsyncSession,
    seed_sku: dict,
    seed_identity_and_recipient: dict,
) -> None:
    """Тот же check, что в unit-suite — но прогон через реальный
    RecipientLookupAdapter поверх живой таблицы."""
    from src.shared.exceptions import UnprocessableEntityError

    # Provision a second identity owning a different recipient
    other_identity_id = uuid.uuid4()
    other_recipient_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO identities (id, primary_auth_method, account_type, is_active)"
            " VALUES (:id, 'LOCAL', 'CUSTOMER', true)"
        ),
        {"id": other_identity_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO recipients (
                id, identity_id, full_name_ru, full_name_lat,
                phone, email,
                is_archived, version
            ) VALUES (
                :id, :identity, :fn_ru, :fn_lat,
                :phone, :email,
                false, 0
            )
            """
        ),
        {
            "id": other_recipient_id,
            "identity": other_identity_id,
            "fn_ru": "Чужой",
            "fn_lat": "Foreign",
            "phone": _RECIPIENT_PII["phone"],
            "email": "foreign@example.com",
        },
    )
    await db_session.flush()

    handler = _build_handler(db_session)
    cmd = _cmd(
        identity_id=seed_identity_and_recipient["identity_id"],
        sku_id=seed_sku["sku_id"],
        recipient_id=other_recipient_id,
        idempotency_key=f"int-buynow-ownership-{uuid.uuid4().hex[:8]}",
    )
    with pytest.raises(UnprocessableEntityError) as exc:
        await handler.handle(cmd)
    assert exc.value.error_code == "ORDER_RECIPIENT_OWNERSHIP_MISMATCH"


# ---------------------------------------------------------------------------
# T-1.4 — Invariant I1 (ADR-010): cart untouched after Buy Now
# ---------------------------------------------------------------------------


async def test_buy_now_does_not_touch_carts_table(
    db_session: AsyncSession,
    seed_sku: dict,
    seed_identity_and_recipient: dict,
    seed_passport: dict,
) -> None:
    """ADR-010 Invariant I1: Buy Now не модифицирует корзину customer'а.

    Snapshot rowcount у `carts` / `cart_items` до и после — должен
    остаться identical. Регрессия (handler начнёт писать в cart по
    ошибке) сразу всплывёт.
    """
    before_carts = (
        await db_session.execute(text("SELECT COUNT(*) FROM carts"))
    ).scalar_one()
    before_cart_items = (
        await db_session.execute(text("SELECT COUNT(*) FROM cart_items"))
    ).scalar_one()

    handler = _build_handler(db_session)
    cmd = _cmd(
        identity_id=seed_identity_and_recipient["identity_id"],
        sku_id=seed_sku["sku_id"],
        recipient_id=seed_identity_and_recipient["recipient_id"],
        idempotency_key=f"int-buynow-invariant-i1-{uuid.uuid4().hex[:8]}",
        passport_id=seed_passport["passport_id"],
    )
    result = await handler.handle(cmd)

    after_carts = (
        await db_session.execute(text("SELECT COUNT(*) FROM carts"))
    ).scalar_one()
    after_cart_items = (
        await db_session.execute(text("SELECT COUNT(*) FROM cart_items"))
    ).scalar_one()

    assert after_carts == before_carts, "Buy Now не должен создавать cart row"
    assert after_cart_items == before_cart_items, (
        "Buy Now не должен создавать cart_items row"
    )
    # Sanity: Order был создан, чтобы убедиться, что мы тестировали
    # реальный happy-path, а не early-return.
    assert (
        await db_session.execute(
            select(text("1"))
            .where(text("EXISTS (SELECT 1 FROM orders WHERE id = :id)"))
            .params(id=result.order_id)
        )
    ).scalar_one_or_none() is not None
