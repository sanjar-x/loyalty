# Architecture Research

**Domain:** E-commerce order lifecycle in a DDD modular monolith (cross-border marketplace aggregator)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Presentation Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ router_cart  │  │ router_order │  │router_order  │  │ router_checkout  │    │
│  │ (customer)   │  │ (customer)   │  │(admin)       │  │ (customer)       │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘    │
├─────────┴──────────────────┴────────────────┴───────────────────┴──────────────┤
│                              Application Layer                                  │
│  ┌─────────────────────┐   ┌──────────────────────┐   ┌────────────────────┐   │
│  │    Cart Commands     │   │   Order Commands     │   │  Order Queries     │   │
│  │ AddToCart            │   │ PlaceOrder           │   │  ListOrders        │   │
│  │ UpdateCartItem       │   │ TransitionStatus     │   │  GetOrder          │   │
│  │ RemoveFromCart       │   │ CancelOrder          │   │  ListOrdersAdmin   │   │
│  │ ClearCart            │   │ AddOrderNote         │   │                    │   │
│  └─────────┬───────────┘   └──────────┬───────────┘   └────────┬───────────┘   │
│            │                          │                         │               │
│  ┌─────────┴──────────────────────────┴─────────────────────────┴───────────┐   │
│  │                    Cross-Module Query Services                           │   │
│  │  ICatalogQueryService (product/SKU snapshots)                           │   │
│  │  ISupplierQueryService (supplier info -- already exists)                │   │
│  │  ICustomerQueryService (customer info for order)                        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
├───────────────────────────────────────────────────────────────────────────────┤
│                              Domain Layer                                      │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐    │
│  │  Cart Aggregate  │   │ Order Aggregate  │   │   Value Objects          │    │
│  │  ├─ CartItem     │   │ ├─ OrderLineItem │   │   OrderStatus (enum)     │    │
│  │  │  (entity)     │   │ │  (VO/entity)   │   │   Money (existing)       │    │
│  │  └───────────────┘   │ ├─ ContactInfo   │   │   DeliveryAddress (VO)   │    │
│  │                      │ │  (VO)          │   │   ProductSnapshot (VO)   │    │
│  │                      │ ├─ OrderNote     │   │   SupplierSource (VO)    │    │
│  │                      │ │  (entity)      │   │   CancellationReason     │    │
│  │                      │ └────────────────┘   │     (enum)               │    │
│  │                      └──────────────────┘   └──────────────────────────┘    │
├───────────────────────────────────────────────────────────────────────────────┤
│                           Infrastructure Layer                                 │
│  ┌───────────────┐  ┌─────────────────┐  ┌───────────────┐  ┌─────────────┐   │
│  │ CartRepo      │  │ OrderRepo       │  │ ORM models.py │  │ Query       │   │
│  │ (SQLAlchemy)  │  │ (SQLAlchemy)    │  │ (Cart, Order, │  │ Services    │   │
│  │               │  │                 │  │  LineItem)     │  │ (catalog,   │   │
│  │               │  │                 │  │               │  │  supplier)  │   │
│  └───────────────┘  └─────────────────┘  └───────────────┘  └─────────────┘   │
├───────────────────────────────────────────────────────────────────────────────┤
│                         Shared Infrastructure                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  UnitOfWork + Outbox  │  RabbitMQ/TaskIQ  │  Dishka DI  │  PostgreSQL │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|---------------|------------------------|
| **Cart Aggregate** | Holds items a customer intends to purchase; enforces per-item and total invariants | Aggregate root with CartItem child entities, keyed by customer_id |
| **Order Aggregate** | Immutable record of a placed order; owns line items, delivery info, status FSM | Aggregate root with OrderLineItem value objects and status state machine |
| **OrderLineItem** | Snapshot of a product/SKU at the time of purchase (price, title, variant, supplier) | Value object embedded in Order; never references live catalog data |
| **Cart-to-Order conversion** | Transforms cart contents into an Order with snapshots of current prices/product data | Application-layer command handler (PlaceOrderHandler), not domain logic |
| **Cross-Module Query Services** | Read-only ports that let the order module fetch data from catalog/supplier/user without importing their internals | Abstract interfaces in order domain; implementations in order infrastructure that query ORM models from other modules |
| **Order Status FSM** | Controls allowed state transitions and emits events on each transition | ClassVar dict on Order aggregate (same pattern as Product._ALLOWED_TRANSITIONS) |

## Recommended Project Structure

```
backend/src/modules/order/
├── domain/
│   ├── entities.py           # Cart, CartItem, Order, OrderLineItem, OrderNote
│   ├── value_objects.py      # OrderStatus, DeliveryAddress, ContactInfo,
│   │                         # ProductSnapshot, SupplierSource, CancellationReason
│   ├── events.py             # OrderPlacedEvent, OrderStatusChangedEvent,
│   │                         # OrderCancelledEvent, CartCheckedOutEvent
│   ├── exceptions.py         # CartEmptyError, InvalidStatusTransitionError,
│   │                         # OrderAlreadyCancelledError, SKUNotAvailableError
│   ├── interfaces.py         # ICartRepository, IOrderRepository,
│   │                         # ICatalogQueryService, ICustomerQueryService
│   └── constants.py          # MAX_CART_ITEMS, ORDER_NUMBER_PREFIX
├── application/
│   ├── commands/
│   │   ├── add_to_cart.py           # AddToCartCommand + Handler
│   │   ├── update_cart_item.py      # UpdateCartItemCommand + Handler
│   │   ├── remove_from_cart.py      # RemoveFromCartCommand + Handler
│   │   ├── clear_cart.py            # ClearCartCommand + Handler
│   │   ├── place_order.py           # PlaceOrderCommand + Handler (cart -> order)
│   │   ├── transition_order_status.py  # TransitionOrderStatusCommand + Handler
│   │   ├── cancel_order.py          # CancelOrderCommand + Handler
│   │   └── add_order_note.py        # AddOrderNoteCommand + Handler
│   ├── queries/
│   │   ├── get_cart.py              # GetCartQuery + Handler
│   │   ├── list_orders.py           # ListOrdersQuery + Handler (customer)
│   │   ├── get_order.py             # GetOrderQuery + Handler
│   │   ├── list_orders_admin.py     # ListOrdersAdminQuery + Handler (admin)
│   │   ├── get_order_admin.py       # GetOrderAdminQuery + Handler (admin)
│   │   └── read_models.py           # Pydantic read models for CQRS read side
│   └── consumers/                   # (future: react to catalog events like
│       └── __init__.py              #  product unpublished -> flag affected orders)
├── infrastructure/
│   ├── models.py             # ORM: CartModel, CartItemModel, OrderModel,
│   │                         # OrderLineItemModel, OrderNoteModel
│   ├── repositories/
│   │   ├── cart_repository.py
│   │   └── order_repository.py
│   └── query_services/
│       ├── catalog_query_service.py  # Reads catalog ORM models directly
│       └── customer_query_service.py # Reads user ORM models directly
├── presentation/
│   ├── router_cart.py        # Customer-facing cart endpoints
│   ├── router_orders.py      # Customer-facing order endpoints
│   ├── router_orders_admin.py # Admin order management endpoints
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── dependencies.py       # Dishka DI provider registration
│   └── mappers.py            # DTO mapping helpers
└── __init__.py
```

### Structure Rationale

- **Single `order` module for both Cart and Order:** Cart is a transient pre-order concept that exists only to feed the Order. Putting them in the same bounded context avoids a cross-module event dance for the most common operation (checkout). The cart-to-order conversion is a single-transaction operation within one module.
- **Cross-module query services in `infrastructure/query_services/`:** These read catalog and user ORM models directly (same pattern as CQRS query handlers reading ORM models). They implement interfaces defined in `domain/interfaces.py`, keeping the domain pure. This follows the existing `ISupplierQueryService` pattern already established in the codebase.
- **Separate admin and customer routers:** Admin endpoints need different auth guards (`RequirePermission(codename="order:manage")`), different query filters (all orders vs. only own orders), and richer response payloads. Splitting routers keeps each clean.
- **`consumers/` directory prepared but mostly empty initially:** The first milestone has no inbound cross-module events to consume. The directory exists for future handlers (e.g., reacting to `ProductStatusChangedEvent` when a product is archived that has open orders).

## Architectural Patterns

### Pattern 1: Cart as Aggregate Root (Server-Side, Per-Customer Singleton)

**What:** The Cart is a persistent aggregate root stored in PostgreSQL, keyed by `customer_id` (one cart per customer). CartItems are child entities. The cart is created lazily on the first `add_to_cart` call.

**When to use:** When the cart needs to persist across sessions, devices, and app restarts -- which is always the case in a Telegram Mini App where users frequently close and reopen the WebApp.

**Trade-offs:**
- PRO: Cart survives app restarts, device switches, and is available to the admin for analytics.
- PRO: Server-side validation of product availability, pricing before items enter the cart.
- CON: Every cart operation is a write (but for this scale, negligible).
- CON: Need to handle stale cart items (product prices changed, SKU deactivated since item was added).

**Example:**
```python
@dataclass
class Cart(AggregateRoot):
    id: uuid.UUID
    customer_id: uuid.UUID
    _items: list[CartItem] = field(factory=list, alias="items")
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))

    @property
    def items(self) -> tuple[CartItem, ...]:
        return tuple(self._items)

    def add_item(
        self,
        *,
        sku_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: uuid.UUID,
        quantity: int = 1,
    ) -> CartItem:
        """Add item or increment quantity if same SKU already in cart."""
        existing = self._find_item_by_sku(sku_id)
        if existing:
            existing.increment_quantity(quantity)
            self.updated_at = datetime.now(UTC)
            return existing
        item = CartItem.create(
            cart_id=self.id,
            sku_id=sku_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
        )
        self._items.append(item)
        self.updated_at = datetime.now(UTC)
        return item

    def clear(self) -> None:
        self._items.clear()
        self.updated_at = datetime.now(UTC)
```

**Why not Redis/client-side:** Persistence guarantees matter more than sub-millisecond latency for a Telegram Mini App. Client-side storage in Telegram WebView is unreliable and size-limited. Redis adds operational complexity for data that already fits naturally in PostgreSQL within the same transaction boundary.

### Pattern 2: Product Snapshot in OrderLineItem (Value Object Embedding)

**What:** When an order is placed, each cart item is "snapshotted" -- the current product title, price, image URL, variant name, and supplier source are copied into the OrderLineItem as value objects. The order never references live catalog data.

**When to use:** Always, for any e-commerce order system. Product data is mutable (prices change, products get deleted), but an order record must preserve what the customer bought and at what price.

**Trade-offs:**
- PRO: Order is self-contained and historically accurate. No broken references when catalog changes.
- PRO: Query performance -- order detail page needs no joins to catalog tables.
- CON: Data duplication (intentional and correct for this domain).
- CON: Snapshot must be complete at placement time (requires a cross-module query service call during checkout).

**Example:**
```python
@frozen
class ProductSnapshot:
    """Immutable snapshot of product data at order placement time."""
    product_id: uuid.UUID
    sku_id: uuid.UUID
    variant_id: uuid.UUID
    title: str              # Resolved from title_i18n at placement time
    variant_name: str       # Resolved from variant name_i18n
    sku_code: str
    image_url: str | None   # Main product image URL at placement time
    slug: str               # For generating "view product" links

@frozen
class SupplierSource:
    """Snapshot of supplier attribution at order placement time."""
    supplier_id: uuid.UUID
    supplier_name: str
    supplier_type: str      # "cross_border" or "local" (from SupplierType enum)

@dataclass
class OrderLineItem:
    """Immutable line item within an Order. Contains full product snapshot."""
    id: uuid.UUID
    product_snapshot: ProductSnapshot
    supplier_source: SupplierSource | None
    unit_price: Money       # Price at time of order
    quantity: int
    line_total: Money       # unit_price * quantity

    @property
    def is_cross_border(self) -> bool:
        return (
            self.supplier_source is not None
            and self.supplier_source.supplier_type == "cross_border"
        )
```

### Pattern 3: Order Status FSM (Domain-Enforced State Machine)

**What:** The Order aggregate owns a status field controlled by a `_ALLOWED_TRANSITIONS` ClassVar dict. Status changes go through `transition_status()` which validates the transition, emits a domain event, and optionally records a timestamp. This is identical to the existing `Product.transition_status()` pattern.

**When to use:** When order lifecycle has well-defined states with business rules about which transitions are valid.

**Trade-offs:**
- PRO: Business rules enforced in the domain, not scattered across handlers.
- PRO: Every transition emits an event for downstream consumers (notifications, analytics).
- PRO: Consistent with existing Product FSM pattern -- team already knows the pattern.
- CON: Adding new states requires a migration (but this is intentional -- state changes should be deliberate).

**Recommended states for this milestone (simplified, extensible):**

```python
class OrderStatus(enum.StrEnum):
    PENDING_PAYMENT = "pending_payment"    # Created, awaiting offline payment
    CONFIRMED       = "confirmed"          # Payment confirmed by admin
    PROCESSING      = "processing"         # Admin is arranging fulfillment
    SHIPPED         = "shipped"            # Items handed to carrier
    DELIVERED       = "delivered"          # Customer received items
    CANCELLED       = "cancelled"          # Cancelled (by admin or customer)

_ALLOWED_TRANSITIONS: ClassVar[dict[OrderStatus, set[OrderStatus]]] = {
    OrderStatus.PENDING_PAYMENT: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED:       {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING:      {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED:         {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED:       set(),  # terminal state
    OrderStatus.CANCELLED:       set(),  # terminal state
}
```

**Why these specific states:** They map to the admin's manual workflow (no payment gateway, no logistics API). `PENDING_PAYMENT` is the initial state (PROJECT.md: "orders created as pending_payment, handled offline"). `PROCESSING` covers the manual supplier communication phase. Future milestones can insert states (e.g., `AWAITING_CUSTOMS`, `AT_PICKUP_POINT`) between `SHIPPED` and `DELIVERED` without breaking existing transitions.

### Pattern 4: Cross-Module Query Service (Read-Only Ports for Module Boundaries)

**What:** The order module defines abstract interfaces (e.g., `ICatalogQueryService`) in its domain layer. Infrastructure implementations query catalog/supplier/user ORM models directly (same database, same process -- this is a modular monolith, not microservices). This follows the established `ISupplierQueryService` pattern.

**When to use:** Whenever a module needs data from another module's aggregates for read purposes. This preserves DDD module boundaries while avoiding the overhead of inter-process calls.

**Trade-offs:**
- PRO: Domain layer stays pure (depends only on interfaces, never on other modules' internals).
- PRO: In a monolith, these are just SQL queries -- no network overhead, no eventual consistency.
- PRO: Easy to test with fakes (same as repository fakes in existing test infrastructure).
- CON: The infrastructure implementation does import other modules' ORM models (acceptable -- excluded from boundary tests like query handlers are).

**Example:**
```python
# In order/domain/interfaces.py
class ICatalogQueryService(ABC):
    @abstractmethod
    async def get_sku_snapshot(
        self, sku_id: uuid.UUID
    ) -> SKUSnapshotDTO | None: ...

    @abstractmethod
    async def get_skus_snapshot_bulk(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SKUSnapshotDTO]: ...

# In order/infrastructure/query_services/catalog_query_service.py
class CatalogQueryService(ICatalogQueryService):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_skus_snapshot_bulk(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SKUSnapshotDTO]:
        # Joins ProductModel, SKUModel, VariantModel, SupplierModel, MediaAssetModel
        # Returns lightweight DTOs with snapshotted data
        ...
```

### Pattern 5: Cart-to-Order Conversion (Application-Layer Orchestration)

**What:** The `PlaceOrderHandler` is an application-layer command handler that:
1. Loads the customer's Cart aggregate
2. Calls `ICatalogQueryService` to get current product/SKU/price snapshots for all cart items
3. Calls `ICustomerQueryService` to get customer contact info
4. Validates all items are still available and prices are current
5. Creates the Order aggregate with snapshotted line items
6. Clears the Cart
7. Commits both operations in a single UoW transaction (Cart clear + Order create = atomic)

**When to use:** Always. Cart-to-order conversion is orchestration logic, not domain logic. The domain entities (Cart, Order) do not know about each other.

**Trade-offs:**
- PRO: Single transaction guarantees no "phantom orders" (order created but cart not cleared, or vice versa).
- PRO: Snapshot validation happens at the application layer where cross-module services are available.
- CON: The handler is somewhat complex (multiple service calls), but this is inherent to the checkout operation.

## Data Flow

### Cart Operations (Customer)

```
Customer (Telegram Mini App)
    │
    ▼
POST /api/backend/orders/cart/items       (via RTK Query + BFF proxy)
    │
    ▼
router_cart.py ─── Depends(RequirePermission("order:cart")) ───►  AddToCartHandler
    │                                                                    │
    ▼                                                                    ▼
AddToCartCommand { customer_id, sku_id, quantity }              ICatalogQueryService
    │                                                           (validate SKU exists,
    ▼                                                            is_active, has price)
ICartRepository.get_by_customer(customer_id)                           │
    │                                                                    │
    ▼                                                                    ▼
Cart.add_item(sku_id, product_id, variant_id, quantity)         Returns SKU data
    │
    ▼
UoW.register_aggregate(cart) → UoW.commit()
    │
    ▼
Response: CartReadModel (items with current prices from catalog query)
```

### Checkout / Place Order (Customer)

```
Customer (Telegram Mini App)
    │
    ▼
POST /api/backend/orders/checkout
    Body: { delivery_address, contact_phone, notes }
    │
    ▼
PlaceOrderHandler
    │
    ├──► ICartRepository.get_by_customer(customer_id)
    │        → Cart with N items
    │
    ├──► ICatalogQueryService.get_skus_snapshot_bulk([sku_ids])
    │        → Current prices, titles, images, supplier info
    │        → Validates all SKUs still active & priced
    │
    ├──► ICustomerQueryService.get_contact_info(customer_id)
    │        → Pre-filled name from Telegram profile
    │
    ▼
    Order.create(
        customer_id, line_items=[snapshotted], delivery_address, contact_info
    )
    → Emits OrderPlacedEvent
    │
    Cart.clear()
    │
    UoW.register_aggregate(order)
    UoW.register_aggregate(cart)
    UoW.commit()  ← single atomic transaction
    │
    ▼
Response: OrderReadModel { order_number, status: "pending_payment", items, total }
```

### Admin Order Status Management

```
Admin (Admin Panel)
    │
    ▼
PATCH /api/backend/admin/orders/{order_id}/status
    Body: { status: "confirmed" }
    │
    ▼
router_orders_admin.py ─── Depends(RequirePermission("order:manage"))
    │
    ▼
TransitionOrderStatusHandler
    │
    ├──► IOrderRepository.get_for_update(order_id)
    │        → Order aggregate (with pessimistic lock)
    │
    ▼
    Order.transition_status(new_status)
    → Validates against _ALLOWED_TRANSITIONS
    → Emits OrderStatusChangedEvent
    │
    UoW.register_aggregate(order)
    UoW.commit()
    │
    ▼
Outbox → TaskIQ → (future: Telegram notification consumer)
```

### Key Data Flows

1. **Cart item addition:** Customer adds SKU to cart -> handler validates SKU exists via `ICatalogQueryService` -> Cart aggregate enforces invariants (max items, no duplicates by SKU) -> persisted.
2. **Cart read with live prices:** `GetCartHandler` loads Cart, then calls `ICatalogQueryService` to enrich each item with *current* product data (price may have changed since item was added). Returns enriched read model. Cart stores only SKU IDs + quantities; prices are always live until checkout.
3. **Checkout snapshot:** `PlaceOrderHandler` fetches current catalog data, freezes it into `ProductSnapshot` and `SupplierSource` value objects embedded in `OrderLineItem`. From this point, the order is self-contained.
4. **Admin status transition:** Admin changes order status -> domain validates FSM -> event emitted to outbox -> (future) consumer sends Telegram notification to customer.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Current design is perfectly adequate. Single PostgreSQL handles all cart + order operations. Cart table stays small (one row per customer). |
| 1k-100k users | Add indexes on `orders.customer_id`, `orders.status`, `orders.created_at`. Consider Redis cache for cart reads if Mini App polling is aggressive. Partition outbox processing by aggregate type. |
| 100k+ users | Consider extracting Cart to Redis for sub-millisecond reads. Orders stay in PostgreSQL. Read-side projections for admin dashboard queries. CQRS read models become essential. |

### Scaling Priorities

1. **First bottleneck:** Admin order listing with complex filters. Solution: proper composite indexes and CQRS read models from day one (already the codebase pattern).
2. **Second bottleneck:** Cart reads during high-traffic periods. Solution: short-lived Redis cache (30s TTL) for cart state, invalidated on writes. Not needed initially.

## Anti-Patterns

### Anti-Pattern 1: Cart References Live Catalog Data at Display Time via Foreign Keys

**What people do:** Make `cart_items.sku_id` a FK to `catalog_skus.id` and JOIN at query time to get product title, price, image.
**Why it's wrong:** When a product is soft-deleted or a SKU is deactivated, the cart JOIN breaks or returns nulls. The cart becomes fragile to catalog changes. The cart read query becomes a multi-table join across module boundaries.
**Do this instead:** Store only `sku_id`, `product_id`, `variant_id` in the cart item (no FK constraint to catalog tables). At cart read time, use `ICatalogQueryService` to enrich items. If a product/SKU is gone, mark the cart item as "unavailable" in the read model rather than crashing.

### Anti-Pattern 2: Order References Live Product Data Instead of Snapshots

**What people do:** Store only `product_id` and `sku_id` in order line items and JOIN to catalog on every order detail query.
**Why it's wrong:** Product title changes, price changes, product deletion all corrupt historical order records. "What did the customer actually buy at what price?" becomes unanswerable.
**Do this instead:** Snapshot all display-relevant product data into OrderLineItem value objects at checkout time. The order table is a self-contained historical record.

### Anti-Pattern 3: Separate Cart and Order Bounded Contexts Communicating via Events

**What people do:** Put Cart in one module and Order in another, with CartCheckedOutEvent triggering order creation asynchronously.
**Why it's wrong for a monolith:** Introduces eventual consistency for what should be an atomic operation. Customer clicks "checkout" and... maybe the order is created a few seconds later? Maybe the event fails and the cart is cleared but no order exists? This complexity makes sense in a distributed system, not in a modular monolith sharing a database.
**Do this instead:** Keep Cart and Order in the same bounded context (`order` module). The `PlaceOrderHandler` converts cart to order in a single transaction. No events needed for this internal operation.

### Anti-Pattern 4: Putting FSM Logic in Command Handlers Instead of the Aggregate

**What people do:** Check allowed transitions in `TransitionOrderStatusHandler` before calling `order.status = new_status`.
**Why it's wrong:** Business invariant enforcement leaks into the application layer. Multiple handlers that touch status must duplicate the validation. The domain model becomes anemic.
**Do this instead:** Put the FSM transition table and validation in the Order aggregate's `transition_status()` method (identical to existing `Product.transition_status()`). The handler just calls `order.transition_status(new_status)` and lets the domain enforce the rules.

### Anti-Pattern 5: Using the `order` Module to Track Inventory/Stock

**What people do:** Decrement stock counters when an order is placed.
**Why it's wrong for this project:** PROJECT.md explicitly states "No warehouse: Pure dropshipping -- no inventory management, stock tracking, or warehouse operations." There is no stock to track. The platform aggregates products from external marketplaces and local suppliers.
**Do this instead:** Nothing. Orders reference SKUs but do not affect any stock count. If inventory tracking is added in a future milestone, it should be a separate bounded context that reacts to OrderPlacedEvent.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|-------------------|-------|
| Telegram WebApp (customer) | RTK Query via BFF proxy (`/api/backend/[...path]`) | Cart and order APIs consumed through existing proxy pattern. No new integration needed. |
| Admin Panel | Server-side `backendFetch()` via BFF routes | Replace `orders.js` seed data service with real API calls to `/admin/orders`. |
| Image Backend | None (direct) | Order snapshots include `image_url` resolved at checkout time. No runtime dependency on image backend. |

### Internal Boundaries (Module-to-Module)

| Boundary | Communication | Direction | Notes |
|----------|--------------|-----------|-------|
| order -> catalog | `ICatalogQueryService` (sync read) | order reads catalog | Query service reads catalog ORM models. Used during add-to-cart validation and checkout snapshotting. Infrastructure implementation excluded from boundary tests (same as query handlers). |
| order -> supplier | `ISupplierQueryService` (sync read) | order reads supplier | Already exists. Used during checkout to snapshot supplier name/type into OrderLineItem. |
| order -> user | `ICustomerQueryService` (sync read) | order reads user | New query service. Reads customer profile for pre-filling contact info during checkout. |
| order -> identity | `RequirePermission` dependency | order uses identity auth | Standard pattern -- no new integration needed. |
| catalog -> order | `OrderPlacedEvent` (async, future) | catalog reacts to order | Future: catalog could track "best sellers" or adjust search ranking. Not needed for this milestone. |
| order -> (outbox) | Domain events via UoW | order emits events | `OrderPlacedEvent`, `OrderStatusChangedEvent`, `OrderCancelledEvent` written to outbox. Consumers wired in future milestones (Telegram notifications, analytics). |

### Cross-Module Query Service Implementation Notes

The existing codebase already has a pattern for cross-module reads: `ISupplierQueryService` is defined in `supplier/domain/interfaces.py` with a `SupplierInfo` DTO. The catalog module depends on this interface and gets the implementation injected via Dishka.

For the order module, define analogous interfaces:

```python
# order/domain/interfaces.py

@dataclass(frozen=True)
class SKUSnapshotDTO:
    """Lightweight DTO for snapshotting SKU data at checkout."""
    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    product_title: str       # Resolved from title_i18n
    variant_name: str        # Resolved from variant name_i18n
    unit_price: Money        # Current price
    image_url: str | None    # Main product image URL
    product_slug: str
    supplier_id: uuid.UUID | None
    supplier_name: str | None
    supplier_type: str | None
    is_available: bool       # SKU is_active AND product is PUBLISHED

class ICatalogQueryService(ABC):
    @abstractmethod
    async def get_skus_snapshot_bulk(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, SKUSnapshotDTO]: ...

@dataclass(frozen=True)
class CustomerContactDTO:
    customer_id: uuid.UUID
    first_name: str
    last_name: str
    phone: str | None
    username: str | None

class ICustomerQueryService(ABC):
    @abstractmethod
    async def get_contact_info(
        self, customer_id: uuid.UUID
    ) -> CustomerContactDTO | None: ...
```

### Boundary Test Updates

The `backend/tests/architecture/test_boundaries.py` `MODULES` list must be updated to include `"order"`. The same exemptions apply: query handlers and consumers can import ORM models from other modules. The domain layer must remain pure.

```python
MODULES = ["catalog", "identity", "user", "order"]
```

## Build Order and Dependencies

Understanding what depends on what determines the implementation sequence:

```
                    ┌─────────────────┐
                    │  1. Domain Layer │
                    │  (entities, VOs, │
                    │   interfaces,    │
                    │   events, FSM)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ 2a. ORM     │  │ 2b. Repos   │  │ 2c. Query   │
    │ Models +    │  │ (Cart,      │  │ Services    │
    │ Migration   │  │  Order)     │  │ (Catalog,   │
    │             │  │             │  │  Customer)  │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
                  ┌──────────────────┐
                  │ 3. Command       │
                  │ Handlers         │
                  │ (Cart ops,       │
                  │  PlaceOrder,     │
                  │  StatusTransition│
                  └────────┬─────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
    ┌──────────────┐ ┌──────────┐ ┌───────────┐
    │ 4a. Query    │ │ 4b. DI   │ │ 4c. Routes│
    │ Handlers     │ │ Wiring   │ │ + Schemas │
    │ (list/get)   │ │ (Dishka) │ │ (FastAPI) │
    └──────────────┘ └──────────┘ └───────────┘
                           │
                  ┌────────┴─────────┐
                  ▼                  ▼
         ┌──────────────┐   ┌──────────────┐
         │ 5. Frontend  │   │ 5. Frontend  │
         │ Admin Panel  │   │ Customer     │
         │ (replace     │   │ Mini App     │
         │  seed data)  │   │ (cart + order│
         │              │   │  pages)      │
         └──────────────┘   └──────────────┘
```

**Critical path:** Domain (1) -> ORM + Repos (2) -> Cart Handlers (3, cart subset) -> Cart API (4) -> Customer Frontend Cart (5). Order handlers and admin frontend can be developed in parallel after step 2.

**Recommended implementation phases:**

1. **Domain + Infrastructure Foundation:** Entities, value objects, FSM, events, ORM models, migration, repositories. Zero API surface yet, but domain logic is unit-testable.
2. **Cart Backend:** Cart command handlers + query handlers + routes. Customer can add/remove/view cart items. Admin has no visibility yet.
3. **Checkout + Order Backend:** PlaceOrder handler, Order query handlers, admin order routes. This is where the cross-module query services get built.
4. **Frontend Integration:** Admin panel replaces seed data with real API. Customer Mini App gets cart UI and checkout flow.

## Sources

- Existing codebase analysis: `backend/src/modules/catalog/domain/entities.py` (Product aggregate with FSM pattern), `backend/src/modules/supplier/domain/interfaces.py` (cross-module query service pattern), `backend/src/infrastructure/outbox/tasks.py` (event handler registration)
- [Walmart: Implementing Cart Service with DDD & Hexagonal Architecture](https://medium.com/walmartglobaltech/implementing-cart-service-with-ddd-hexagonal-port-adapter-architecture-part-2-d9c00e290ab)
- [SSENSE: DDD Beyond the Basics - Mastering Aggregate Design](https://medium.com/ssense-tech/ddd-beyond-the-basics-mastering-aggregate-design-26591e218c8c)
- [Martin Fowler: DDD Aggregate](https://martinfowler.com/bliki/DDD_Aggregate.html)
- [Implementing Order Aggregate Pattern in .NET - DDD Example](https://ilovedotnet.org/blogs/ddd-implementing-order-aggregate-pattern-in-dotnet/)
- [commercetools: State Machines for Order Lifecycle](https://docs.commercetools.com/learning-model-your-business-structure/state-machines/state-machines-page)
- [Spring Boot DDD E-Commerce Order Management System](https://dev.to/devcorner/spring-boot-ddd-e-commerce-order-management-system-detailed-walkthrough-12ie)
- [SAP: How to Develop Aggregates](https://github.com/SAP/curated-resources-for-domain-driven-design/blob/main/blog/0004-how-to-develop-aggregates.md)
- [ABP.IO: Integrating Modules via Messages/Events](https://abp.io/docs/latest/tutorials/modular-crm/part-07)

---
*Architecture research for: E-commerce order lifecycle (DDD modular monolith)*
*Researched: 2026-03-28*
