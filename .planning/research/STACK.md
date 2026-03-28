# Stack Research: Order Lifecycle Management

**Domain:** E-commerce order lifecycle (cart, checkout, orders, admin management) in an existing DDD modular monolith
**Researched:** 2026-03-28
**Confidence:** HIGH

## Recommended Stack

This research covers only **new** technologies and patterns needed for the order lifecycle milestone. The existing stack (Python 3.14, FastAPI, SQLAlchemy 2.1, PostgreSQL, attrs, Dishka, TaskIQ/RabbitMQ, Transactional Outbox) is established and not re-evaluated here.

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Hand-rolled FSM (dict-based transition table) | N/A | Order state machine | The codebase already uses this exact pattern in `Product.transition_status()` with `_ALLOWED_TRANSITIONS: ClassVar[dict]`. Consistency trumps library features; the order FSM has ~6 states and ~8 transitions -- well within hand-rolled territory. Adding a library dependency for this would violate the existing architectural style for zero benefit. |
| `Decimal` (stdlib) via existing `Money` value object | N/A | Price snapshotting in orders | The codebase already has a battle-tested `Money` frozen value object (`catalog/domain/value_objects.py`) storing amounts as integer subunits (kopecks). Reuse it in the order module -- no new dependency needed. |
| PostgreSQL JSONB (via SQLAlchemy `JSONB` type) | Already in stack | Order item snapshots (product title, price, variant info at time of purchase) | Orders must capture a point-in-time snapshot of product data. JSONB columns on the `order_items` table store denormalized product/variant/SKU details so orders remain valid even if products are later modified or deleted. Already supported by the existing SQLAlchemy + asyncpg stack. |
| Redis (existing) | Already in stack | Cart storage | Carts are ephemeral, high-write, low-durability structures. Redis hashes with TTL provide sub-millisecond reads/writes, automatic expiration of abandoned carts, and zero database load. The existing Redis infrastructure (redis 7.3, hiredis) handles this with no additions. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| No new Python dependencies required | -- | -- | The order module is built entirely on the existing stack. The patterns (attrs entities, CQRS handlers, Dishka DI, Transactional Outbox events, Pydantic schemas) are identical to the `catalog` module. |

### Key Patterns (Not Libraries)

These are architectural patterns implemented with existing tools, not new dependencies:

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| Cart-as-Redis-Hash | `HSET cart:{user_id} sku:{sku_id} {json_payload}` with 7-day TTL | Ephemeral cart storage. Each hash field is a cart line item with quantity, snapshot price, and SKU reference. |
| Cart-to-Order Conversion | Command handler reads Redis cart, validates SKU availability/prices, creates `Order` aggregate with `OrderItem` child entities, then deletes the cart key | Atomic checkout flow. Cart is ephemeral (Redis); Order is durable (PostgreSQL). |
| Order Item Snapshot | `OrderItem` stores denormalized product_title, variant_name, sku_code, unit_price, quantity, supplier_id, source_type at creation time | Immutable record of what was ordered. Never joins back to product tables for display. |
| Order FSM with Guarded Transitions | `Order._ALLOWED_TRANSITIONS` dict + `Order.transition_status()` method, identical to `Product.transition_status()` | Enforces valid state changes, emits `OrderStatusChangedEvent` domain events, uses `object.__setattr__` bypass for guarded fields. |
| Outbox Events for Order Lifecycle | `OrderCreatedEvent`, `OrderStatusChangedEvent`, `OrderCancelledEvent` as `DomainEvent` subclasses | Cross-module communication (future: notifications, analytics, logistics). Already supported by the Transactional Outbox + RabbitMQ infrastructure. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Alembic (existing) | Order module migrations | Follow existing date-based subdirectory convention. Single migration for `orders`, `order_items`, and `order_status_history` tables. |
| pytest + testcontainers (existing) | Order module tests | Follow existing test structure: `tests/unit/order/`, `tests/integration/order/`, `tests/e2e/order/`. |
| pytest-archon (existing) | Architecture boundary enforcement | Add `order` module to existing boundary rules in `tests/architecture/test_boundaries.py`. |

## Installation

```bash
# No new dependencies needed.
# The order module uses only existing stack components.
#
# If starting from scratch:
cd backend
uv sync  # installs all existing deps from uv.lock
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| Hand-rolled FSM (dict table) | `python-statemachine` 3.0.0 | When the FSM has 15+ states, compound/parallel states, or needs visual diagram generation. Order lifecycle has ~6 states -- a library adds coupling without proportional value. The existing codebase already has the hand-rolled pattern; switching one module to a library while others use dicts would be inconsistent. |
| Hand-rolled FSM (dict table) | `transitions` 0.9.4 | When you need hierarchical state machines with nested states or dynamic model decoration. Same consistency argument applies. `transitions` also decorates model instances with trigger methods, which conflicts with the codebase's guarded-field pattern (`__setattr__` override). |
| Redis Hash for cart | PostgreSQL `carts` table | When cart data must survive Redis restarts (e.g., high-value B2B carts). For this marketplace with ~$20-200 average order values and manual payment, Redis with 7-day TTL is appropriate. Lost carts are a minor UX annoyance, not a business crisis. |
| Redis Hash for cart | Client-side cart (localStorage in Telegram Mini App) | When zero backend infrastructure is desired. Not viable here because: (a) Telegram Mini Apps have limited localStorage, (b) cart must be validated server-side before checkout, (c) admin needs visibility into abandoned carts later. |
| JSONB snapshot on OrderItem | Separate `order_item_snapshots` table with normalized columns | When you need to query across historical snapshots (e.g., "all orders containing product X"). For this milestone, JSONB on the order_items row is simpler and queries are always by order_id, not by product attributes across orders. |
| Existing `Money` VO (integer subunits) | `immoney` 0.11.0 | When multi-currency arithmetic with Overdraft types is needed. This platform uses single-currency (RUB) with admin-set prices. The existing `Money(amount=int, currency=str)` frozen VO is sufficient. `immoney` requires Python >=3.10 (compatible) but adds conceptual overhead (SubunitFraction, Overdraft) that this domain does not need. |
| Existing `Money` VO | `stockholm` | When you need GraphQL/Protobuf serialization of monetary amounts. Not applicable here. |
| `structlog` event logging for audit | Dedicated `order_audit_log` table | When regulatory compliance requires tamper-evident audit trails. For now, order status history is captured via `order_status_history` table (who changed what, when) and domain events in the outbox. A dedicated audit table can be added later without architectural changes. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `python-statemachine` or `transitions` for Order FSM | Adds an external dependency for a 6-state machine when the codebase already has a proven hand-rolled pattern (`Product._ALLOWED_TRANSITIONS`). Library mixins/decorators conflict with the project's attrs + AggregateRoot + guarded-field conventions. Would be the only module using a state machine library, creating inconsistency. | Hand-rolled dict-based FSM transition table on the Order aggregate, identical to Product's pattern. |
| SQLAlchemy `Enum` type for order status column | PostgreSQL native enums cannot be altered without migration gymnastics (`ALTER TYPE ... ADD VALUE` is not transactional). Adding new order states later (e.g., `awaiting_shipment`, `partially_fulfilled`) would require careful migration. | `String` / `VARCHAR` column storing `StrEnum.value`. Validate at the domain layer (Order entity), not at the database layer. Same pattern used by `ProductStatus` in the catalog module. |
| Celery for async order processing | The project already uses TaskIQ + RabbitMQ with Dishka integration. Celery would be a parallel, redundant task system with its own broker config, worker lifecycle, and DI story. | TaskIQ tasks triggered via the existing Transactional Outbox relay pattern. |
| SQLModel | Combines Pydantic + SQLAlchemy models into one class. Conflicts with the project's strict layer separation (domain entities are attrs classes, ORM models are separate SQLAlchemy declarative classes, schemas are Pydantic). | Keep the existing clean separation: attrs domain entities, SQLAlchemy ORM models, Pydantic request/response schemas. |
| Event Sourcing for orders | Full event sourcing (append-only event store, projections, event replay) is massive architectural overhead. The existing Transactional Outbox pattern already captures domain events for cross-module communication. Order state is simple enough for CRUD + status history table. | Standard CRUD with Order aggregate + `order_status_history` table for audit trail + Transactional Outbox for event propagation. |
| Separate Cart microservice | The project is a modular monolith. Extracting cart into a separate service adds network latency, deployment complexity, and distributed transaction headaches for a team that doesn't need independent scaling yet. | Cart as a thin infrastructure concern (Redis operations in the `order` module's infrastructure layer), not a separate bounded context. |
| Floating-point for prices | IEEE 754 floating-point arithmetic causes rounding errors in financial calculations (e.g., `0.1 + 0.2 != 0.3`). | Use the existing `Money` value object which stores amounts as integer subunits (kopecks). All arithmetic happens on integers. |

## Stack Patterns by Variant

**Cart storage pattern:**
- Use Redis Hash (`cart:{user_id}`) with fields per SKU ID
- Each field value is a JSON string: `{"sku_id": "...", "quantity": 2, "added_at": "...", "price_snapshot": {"amount": 15000, "currency": "RUB"}}`
- Set TTL on the cart key (7 days) for automatic abandoned cart cleanup
- Cart operations are infrastructure-level (no domain entity for Cart -- it's a transient data structure, not a business aggregate)
- Because: Cart has no meaningful invariants beyond "quantity > 0" and "SKU exists". Making it a full DDD aggregate with repository + UoW adds ceremony without business value. The real invariants (price validation, SKU availability) are checked at checkout time.

**Order aggregate pattern:**
- `Order` is an AggregateRoot (attrs `@dataclass`) owning `OrderItem` child entities
- Order stores: customer_id, status, delivery_address (text), contact_phone, contact_name, notes, total_amount (Money), created_at, updated_at
- OrderItem stores: sku_id (reference), quantity, unit_price (Money), product_snapshot (JSONB dict with title, variant, sku_code, image_url, supplier info)
- Order.create() factory method calculates total from items, sets status to `pending_payment`
- Because: This follows the exact same aggregate pattern as `Product` with owned child entities (`ProductVariant`, `SKU`)

**Order status flow (simplified for this milestone):**
- `pending_payment` -> `confirmed` -> `processing` -> `shipped` -> `delivered`
- `pending_payment` -> `cancelled` (customer cancellation)
- `confirmed` -> `cancelled` (admin cancellation)
- `processing` -> `cancelled` (admin cancellation before shipment)
- Because: Designed for extensibility. Future states (`awaiting_shipment`, `partially_fulfilled`, `refunded`) can be added by extending the transition dict without structural changes.

**If full event sourcing is needed later:**
- The Transactional Outbox already captures all order events
- Add a read-side projection that materializes from outbox events
- No architectural rewrite needed -- just add consumers
- Because: The outbox pattern is a stepping stone to event sourcing if the business requires it

## Version Compatibility

| Package | Compatible With | Notes |
|---------|----------------|-------|
| attrs >=25.4.0 | Python 3.14, SQLAlchemy 2.1 | Used for Order and OrderItem domain entities. `@dataclass` (from attrs, not stdlib) and `@frozen` for value objects. Confirmed working in existing catalog module. |
| SQLAlchemy >=2.1.0b1 | asyncpg >=0.31.0, PostgreSQL 18 | JSONB type for order item snapshots. `MutableDict.as_mutable(JSONB)` if change tracking is needed (unlikely for immutable snapshots). |
| redis >=7.3.0 | Python 3.14 | Async Redis client for cart operations. Already configured with hiredis C extension. |
| Pydantic (via FastAPI) | Python 3.14 | Request/response schemas for order endpoints. Pydantic v2 `condecimal` / `conint` for price validation at the API boundary. |
| Dishka >=1.9.1 | FastAPI, TaskIQ | DI for order command/query handlers, repository implementations. Same provider pattern as existing modules. |

## Order Module Structure (Following Existing Convention)

```
backend/src/modules/order/
    domain/
        entities.py       # Order (AggregateRoot), OrderItem (child entity)
        value_objects.py   # OrderStatus (StrEnum), DeliveryAddress, ContactInfo
        events.py          # OrderCreatedEvent, OrderStatusChangedEvent, OrderCancelledEvent
        exceptions.py      # InvalidOrderTransitionError, EmptyCartError, etc.
        interfaces.py      # IOrderRepository, ICartService (port)
    application/
        commands/          # CreateOrderCommand, CancelOrderCommand, UpdateOrderStatusCommand
        queries/           # GetOrderQuery, ListOrdersQuery (admin), ListCustomerOrdersQuery
    infrastructure/
        repositories/      # SQLAlchemy OrderRepository
        cart/              # RedisCartService (implements ICartService port)
        models.py          # ORM models: OrderModel, OrderItemModel, OrderStatusHistoryModel
        provider.py        # Dishka DI wiring
    presentation/
        router_customer.py # POST /cart/items, DELETE /cart/items/{sku_id}, POST /checkout, GET /orders
        router_admin.py    # GET /admin/orders, GET /admin/orders/{id}, PATCH /admin/orders/{id}/status
        schemas.py         # Pydantic request/response models
        dependencies.py    # Dishka providers for order module
```

## Sources

- [python-statemachine PyPI](https://pypi.org/project/python-statemachine/) -- v3.0.0 released 2026-02-24, Python >=3.9. Evaluated and rejected for consistency reasons. **MEDIUM confidence** (verified via PyPI).
- [transitions GitHub](https://github.com/pytransitions/transitions) -- v0.9.4, lightweight FSM. Evaluated and rejected due to model decoration conflicts with attrs guarded fields. **MEDIUM confidence** (verified via GitHub).
- [Existing Product FSM pattern](../codebase/ARCHITECTURE.md) -- `Product._ALLOWED_TRANSITIONS` dict + `transition_status()` method. **HIGH confidence** (verified in codebase).
- [Existing Money value object](../codebase/STACK.md) -- `Money(amount=int, currency=str)` frozen attrs class with integer subunit storage. **HIGH confidence** (verified in codebase).
- [Redis shopping cart patterns](https://redis.io/learn/howtos/shoppingcart) -- Redis hashes for cart storage, industry standard pattern. **MEDIUM confidence** (Redis official docs).
- [immoney PyPI](https://pypi.org/project/immoney/) -- v0.11.0, released 2024-10-19, Python >=3.10. Evaluated and rejected as overkill for single-currency use case. **MEDIUM confidence** (verified via PyPI).
- [Walmart cart DDD article](https://medium.com/walmartglobaltech/implementing-cart-service-with-ddd-hexagonal-port-adapter-architecture-part-1-4dab93b3fa9f) -- Cart as aggregate in hexagonal architecture. **LOW confidence** (single blog post, but aligns with DDD literature).
- [PostgreSQL JSONB in SQLAlchemy 2.1](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html) -- JSONB type documentation. **HIGH confidence** (official docs).

---
*Stack research for: Order lifecycle management in existing DDD modular monolith*
*Researched: 2026-03-28*
