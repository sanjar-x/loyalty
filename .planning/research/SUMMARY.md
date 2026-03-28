# Project Research Summary

**Project:** LoyaltyMarket — Cross-border e-commerce marketplace aggregator
**Domain:** Order lifecycle management (cart, checkout, orders, admin fulfillment) in an existing DDD modular monolith
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

LoyaltyMarket needs an order lifecycle module built into its existing Python/FastAPI DDD modular monolith. The platform aggregates products from Chinese marketplaces (Poizon, Taobao, 1688) and local Russian suppliers, selling through a Telegram Mini App with a separate admin panel. The research conclusively shows that **no new dependencies are required** -- the existing stack (Python 3.14, FastAPI, SQLAlchemy 2.1, PostgreSQL, attrs, Dishka, TaskIQ/RabbitMQ, Transactional Outbox) fully covers every need. The order module follows identical patterns to the existing catalog module: attrs domain entities, hand-rolled FSM with dict-based transition tables, CQRS command/query handlers, and Dishka DI wiring. The most critical architectural decision is to use a **server-side cart persisted in PostgreSQL** (not Redis, not localStorage) within the same `order` bounded context, enabling atomic cart-to-order conversion in a single database transaction.

The recommended approach is to model the state machine at the **OrderItem level, not the Order level**. This is the single most important design decision. The platform's core value proposition is mixing cross-border and local items in one order, which means items progress through fulfillment independently (a local item ships in 2 days while a Poizon sneaker takes 14 days through customs). A flat order-level state machine cannot represent this and would require an expensive rewrite once real orders arrive. The Order aggregate's status should be a computed property derived from its child items' statuses.

The key risks are: (1) the outbox relay silently discards unknown event types, which must be fixed before deploying order event producers or events will be permanently lost; (2) the admin frontend has a sophisticated filter/sort/tab system built against seed data with specific status strings and response shapes -- the backend API must match this contract exactly or orders will silently disappear from the UI; (3) customer PII (passport data, INN for customs) requires encryption at rest given Russian data protection requirements. All three risks have clear mitigation strategies documented in the pitfalls research.

## Key Findings

### Recommended Stack

No new Python dependencies are needed. The order module is built entirely on the existing stack, following the same patterns established in the catalog module. See [STACK.md](./STACK.md) for full details.

**Core technologies (all existing):**
- **Hand-rolled FSM (dict-based transition table):** Order/item status management -- consistent with `Product.transition_status()` pattern already in the codebase
- **PostgreSQL JSONB (via SQLAlchemy):** Product snapshots in order line items -- captures point-in-time product data so orders survive catalog changes
- **PostgreSQL (not Redis):** Server-side cart storage -- persistence guarantees matter more than sub-millisecond latency for a Telegram Mini App; keeps cart and order in the same transaction boundary
- **Existing Money value object (integer subunits):** Price handling in orders -- already battle-tested, stores amounts as kopecks, eliminates floating-point arithmetic errors
- **Transactional Outbox + RabbitMQ/TaskIQ:** Order domain events -- enables future notifications and analytics without architectural changes

**Critical version notes:** None. All existing dependencies are compatible. `uv sync` installs everything needed.

### Expected Features

The existing admin and customer frontends already have significant UI scaffolding (seed data, filter hooks, status tabs, checkout forms) that needs to be connected to real backend APIs. See [FEATURES.md](./FEATURES.md) for the full feature landscape.

**Must have (table stakes -- P1):**
- Server-side cart with CRUD (add, update quantity, remove, clear) -- replaces `useCart` stub
- Checkout flow collecting recipient info, delivery address, and customs data for cross-border items
- Order creation with product snapshots, supplier attribution, and per-item status tracking
- Order state machine with 7 internal states mapped to 5 customer-facing statuses
- Admin order list with status tabs, search, date filtering, sort -- replacing seed data with real API
- Admin per-item status management with Chinese tracking number input
- Customer order list and detail views -- replacing empty arrays with real data

**Should have (differentiators -- P2):**
- Telegram bot notifications on order status changes (near-100% delivery rate vs email/SMS)
- Order history audit log (every status change recorded with who/when/why)
- Admin notes/comments on orders (team communication)
- Cancellation reason tracking (operational intelligence)

**Defer (v2+):**
- Payment gateway integration (PCI scope, refund flows -- keep offline payment)
- Logistics API integration (CDEK, Pochta, Yandex -- keep manual tracking)
- Automated pricing/currency conversion (keep admin-set RUB prices)
- Customer self-service cancellation (cross-border makes this dangerous)
- Promo code/discount engine (disproportionate effort for early stage)

### Architecture Approach

Cart and Order live in a single `order` bounded context within the modular monolith. Cart is a persistent aggregate root in PostgreSQL (one per customer, created lazily). Order is an aggregate root owning OrderLineItem child entities, each containing immutable product snapshots. Cross-module data access uses query service interfaces (e.g., `ICatalogQueryService`) defined in the order domain layer, with infrastructure implementations that read catalog ORM models directly -- same pattern as the existing `ISupplierQueryService`. Cart-to-order conversion happens in a single UoW transaction (atomic: cart cleared + order created). See [ARCHITECTURE.md](./ARCHITECTURE.md) for full component diagrams and data flows.

**Major components:**
1. **Cart Aggregate** -- holds items a customer intends to purchase; per-customer singleton in PostgreSQL; no FK constraints to catalog (uses query services for enrichment)
2. **Order Aggregate with OrderLineItem children** -- immutable record of what was purchased; each line item has its own status FSM and product snapshot; order-level status is computed
3. **Cross-Module Query Services** -- `ICatalogQueryService` (product/SKU snapshots for checkout), `ICustomerQueryService` (pre-fill contact info from Telegram profile)
4. **PlaceOrderHandler** -- application-layer orchestrator that loads cart, snapshots catalog data, validates availability/prices, creates order, clears cart in one transaction
5. **Presentation Layer** -- separate routers for customer cart, customer orders, and admin order management with different auth guards and response payloads

### Critical Pitfalls

Top 7 pitfalls ranked by recovery cost. See [PITFALLS.md](./PITFALLS.md) for the complete analysis.

1. **Flat order-level state machine** -- Design FSM at the OrderItem level from day one. Order status is a computed property. Recovery cost if missed: HIGH (database migration, logic rewrite, 2-3 sprint disruption).
2. **Outbox relay silently discards unknown event types** -- Fix the relay bug (lines 137-147 in `relay.py`) before deploying order events. Register handlers even as no-ops. Recovery cost if missed: HIGH (lost events are unrecoverable).
3. **Missing product/price snapshots in order items** -- Snapshot all display-relevant data into OrderLineItem at checkout. Never join back to catalog tables for order display. Recovery cost if missed: HIGH (historical price accuracy permanently lost).
4. **Client-side-only cart** -- Must be server-side from the start. Telegram Mini App localStorage is unreliable across restarts. Recovery cost if missed: MEDIUM.
5. **Missing optimistic locking on orders** -- Add `version` field to Order aggregate following existing Supplier entity pattern. Return HTTP 409 on concurrent modifications. Recovery cost if missed: MEDIUM.
6. **Cross-module coupling (order imports catalog entities)** -- Use `ICatalogQueryService` interface + infrastructure adapter. Enforce with pytest-archon boundary rules. Recovery cost if missed: MEDIUM.
7. **Admin UI/API status string mismatch** -- Document the status contract before implementation. Backend enum values must match seed data strings exactly (`placed`, `in_transit`, `pickup_point`, `canceled`, `received`). Recovery cost if missed: LOW but insidious.

## Implications for Roadmap

Based on combined research, here is the recommended phase structure. The ordering is driven by three factors: (1) dependency chains from the architecture build order, (2) the "fix infrastructure bugs before they eat your events" principle, and (3) grouping backend and frontend work that shares the same domain context.

### Phase 0: Infrastructure Pre-Work
**Rationale:** The outbox relay bug (silently discarding unknown event types) must be fixed before any order events are emitted. This is a prerequisite, not optional. Without this fix, `OrderCreatedEvent` and `OrderStatusChangedEvent` will be silently consumed and permanently lost.
**Delivers:** Fixed outbox relay (unknown events left unprocessed or moved to dead-letter table), monitoring query for stale unprocessed events, order event handler stubs registered in relay.
**Addresses:** No features directly -- pure infrastructure hardening.
**Avoids:** Pitfall 6 (outbox events lost for new order event types).

### Phase 1: Domain Foundation
**Rationale:** Everything depends on the domain layer. Entities, value objects, FSM, events, exceptions, and interfaces must exist before any handler, repository, or API can be built. Getting the OrderItem-level FSM right here prevents the most expensive pitfall.
**Delivers:** `Order` aggregate root, `OrderLineItem` with per-item status FSM, `Cart` aggregate, all value objects (`OrderStatus`, `ProductSnapshot`, `SupplierSource`, `DeliveryAddress`, `ContactInfo`, `Money` reuse), domain events, repository interfaces, cross-module query service interfaces. ORM models and Alembic migration for `orders`, `order_items`, `order_status_history`, `carts`, `cart_items` tables. Repository implementations. Unit tests for FSM transitions, aggregate invariants, and value object equality.
**Addresses:** Order state machine (FEATURES P1), order creation data model (FEATURES P1), optimistic locking (version field).
**Avoids:** Pitfall 1 (flat state machine), Pitfall 2 (missing snapshots), Pitfall 4 (missing optimistic locking), Pitfall 5 (cross-module coupling).

### Phase 2: Cart and Checkout Backend
**Rationale:** Cart is a prerequisite for order creation. The checkout flow is the cart-to-order conversion that connects the two aggregates. Building these together keeps the transactional boundary clean (single UoW commit for cart clear + order create).
**Delivers:** Cart command handlers (add, update, remove, clear), cart query handler (get cart with live prices from catalog), checkout/PlaceOrder command handler (validates cart, snapshots products, creates order, clears cart atomically), cart API routes (`POST /cart/items`, `DELETE /cart/items/{sku_id}`, `PATCH /cart/items/{sku_id}`, `GET /cart`), checkout API route (`POST /checkout`). Cross-module query service implementations (`CatalogQueryService`, `CustomerQueryService`). Dishka DI wiring.
**Addresses:** Cart backend (FEATURES P1), checkout flow (FEATURES P1), order creation (FEATURES P1).
**Avoids:** Pitfall 3 (client-side-only cart), Pitfall 2 (price drift at checkout -- re-validates prices).

### Phase 3: Order Management Backend
**Rationale:** With orders being created via checkout, the backend now needs query and status-management endpoints for both admin and customer views. Admin order management is the primary daily workflow -- the order list with filters, detail view, and per-item status updates.
**Delivers:** Customer order endpoints (`GET /orders`, `GET /orders/{id}`), admin order endpoints (`GET /admin/orders` with pagination/filtering/sorting, `GET /admin/orders/{id}`, `PATCH /admin/orders/{id}/items/{item_id}/status`), order status transition logic with audit trail (`OrderStatusHistory` records), human-readable order number generation (e.g., `LM-20260328-00001`). Integration tests verifying API response shapes match admin frontend expectations.
**Addresses:** Admin order list/detail/per-item management (FEATURES P1), customer order list/detail (FEATURES P1), order status transitions (FEATURES P1).
**Avoids:** Pitfall 7 (admin UI/API contract mismatch -- response shape validated by integration tests).

### Phase 4: Frontend Integration
**Rationale:** Backend APIs are complete and tested. Frontend work replaces seed data and stubs with real API calls. Admin and customer frontends can be developed in parallel since they consume independent API surfaces.
**Delivers:** Customer Mini App -- `useCart` hook connected to real cart API via RTK Query, checkout page connected to `POST /checkout`, order list/detail pages connected to real order API. Admin Panel -- `getOrders()` service replaced with real API calls, `OrderStatusModal` connected to per-item status endpoint, `TopMetrics` driven by real data. Incremental replacement: first make API return seed-compatible shapes, then swap data source.
**Addresses:** Cart frontend integration (FEATURES P1), all admin order management UI (FEATURES P1), all customer order views (FEATURES P1).
**Avoids:** Pitfall 7 (admin UI/API mismatch -- incremental replacement strategy).

### Phase 5: Hardening and Notifications (v1.x)
**Rationale:** Core order lifecycle is live. This phase adds operational maturity features triggered by real usage data.
**Delivers:** Telegram bot notifications on order status changes (via outbox consumer), rate limiting on order creation endpoint, idempotency key support on checkout, PII encryption for customs data (passport, INN), admin order notes, cancellation reason tracking.
**Addresses:** Telegram notifications (FEATURES P2), order history audit log (FEATURES P2), admin notes (FEATURES P2), cancellation reasons (FEATURES P2).
**Avoids:** Security pitfalls (PII exposure, missing rate limiting, duplicate order creation).

### Phase Ordering Rationale

- **Phase 0 before everything** because the outbox bug causes silent, permanent data loss for order events. Deploying order features without this fix means lost events that cannot be recovered.
- **Phase 1 before Phase 2** because cart handlers and checkout handlers depend on domain entities, repository interfaces, and ORM models. The domain layer is the foundation.
- **Phase 2 before Phase 3** because order management endpoints are meaningless without orders to manage. Checkout must be functional first.
- **Phase 3 before Phase 4** because frontend integration requires stable, tested backend APIs. Building frontend against shifting APIs creates waste.
- **Phase 4 can partially overlap Phase 3** -- the cart frontend can be built as soon as Phase 2 completes, while admin frontend waits for Phase 3 admin endpoints.
- **Phase 5 is post-launch** -- triggered by operational metrics, not scheduled by date.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Cart and Checkout):** The cart-to-order conversion involves multiple cross-module query service calls in a single transaction. The exact data shape returned by `ICatalogQueryService.get_skus_snapshot_bulk()` needs careful design to include all fields the frontend needs. Research the existing catalog ORM model joins to determine what is efficiently queryable.
- **Phase 4 (Frontend Integration):** The admin frontend has 1,645 lines in `checkout/page.tsx` and complex filter hooks built against seed data. The exact contract between API responses and frontend expectations needs mapping before implementation. The existing `resolveOrderStatus()` function and `useOrderFilters` hook define the contract from the frontend side.

Phases with standard patterns (skip `/gsd:research-phase`):
- **Phase 0 (Infrastructure Pre-Work):** Small, well-scoped bug fix in the outbox relay. The fix is already identified (remove lines 137-147 that mark unknown events as processed).
- **Phase 1 (Domain Foundation):** Follows established patterns from the catalog module exactly. The entity, repository, and FSM patterns are directly portable.
- **Phase 3 (Order Management Backend):** Standard CQRS query handlers and FastAPI routes. Follows existing catalog module patterns.

## Confidence Assessment

| Area         | Confidence | Notes |
| ------------ | ---------- | ----- |
| Stack        | HIGH       | No new dependencies needed. All technologies are already in production in the catalog module. Sources include codebase analysis and official documentation. |
| Features     | HIGH       | Extensive existing frontend scaffolding (seed data, UI components, hooks) defines feature requirements precisely. Competitor analysis and Baymard UX research validate table-stakes list. |
| Architecture | HIGH       | Architecture follows existing codebase patterns verbatim (same aggregate style, same CQRS pattern, same DI wiring, same outbox events). Multiple DDD and e-commerce architecture sources confirm the approach. |
| Pitfalls     | HIGH       | Pitfalls are grounded in codebase analysis (specific file references, line numbers) and validated against industry patterns (Shopify split-order, Sylius concurrency bugs, commercetools state machines). |

**Overall confidence:** HIGH

### Gaps to Address

- **Per-item vs per-order status derivation logic:** The exact algorithm for computing order-level display status from item-level statuses needs specification during Phase 1 planning. The frontend's `resolveOrderStatus()` provides a starting point but uses string comparisons against seed data statuses that may not map 1:1 to the backend's richer internal states.
- **Customs data encryption approach:** Phase 5 calls for PII encryption at rest, but the specific encryption library, key management strategy, and performance impact on queries are not researched. This needs investigation before Phase 5 planning.
- **Order number format:** The "Looks Done But Isn't" checklist flags that UUIDs are unfriendly for phone support. The exact format (e.g., `LM-YYYYMMDD-NNNNN`) and uniqueness guarantee mechanism (database sequence vs. application logic) need specification in Phase 1.
- **Cart staleness handling:** When a user returns to a cart with items whose products have been deactivated or repriced, the UX for handling stale items (remove automatically? show warning? update price silently?) is not fully specified.
- **Admin bulk status updates:** Identified as a UX pitfall but not included in any phase. If admin processes 50+ orders daily, this becomes operationally necessary. Monitor after launch.

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: catalog module domain entities, supplier query service pattern, Product FSM, Money value object, outbox relay implementation, admin seed data and filter hooks, customer checkout page and cart stub
- Project documentation: `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`
- [SQLAlchemy 2.1 PostgreSQL JSONB docs](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html)
- [Redis shopping cart patterns](https://redis.io/learn/howtos/shoppingcart) (evaluated and rejected in favor of PostgreSQL for this use case)

### Secondary (MEDIUM confidence)
- [Baymard Institute Checkout UX Research 2025](https://baymard.com/blog/current-state-of-checkout-ux)
- [ArchiMetric UML State Machine for E-Commerce](https://www.archimetric.com/case-study-uml-state-machine-diagram-for-e-commerce-order-lifecycle/)
- [commercetools State Machine Documentation](https://docs.commercetools.com/learning-model-your-business-structure/state-machines/state-machines-page)
- [Walmart: Implementing Cart Service with DDD & Hexagonal Architecture](https://medium.com/walmartglobaltech/implementing-cart-service-with-ddd-hexagonal-port-adapter-architecture-part-2-d9c00e290ab)
- [SSENSE: DDD Beyond the Basics - Mastering Aggregate Design](https://medium.com/ssense-tech/ddd-beyond-the-basics-mastering-aggregate-design-26591e218c8c)
- [Martin Fowler: DDD Aggregate](https://martinfowler.com/bliki/DDD_Aggregate.html)
- [python-statemachine PyPI](https://pypi.org/project/python-statemachine/) (evaluated and rejected)
- [transitions GitHub](https://github.com/pytransitions/transitions) (evaluated and rejected)

### Tertiary (LOW confidence)
- [Shopify: How to Manage Split Orders](https://www.shopify.com/blog/split-order) -- sub-order pattern validation
- [Sylius: Race conditions in inventory tracking, order, payment status](https://github.com/Sylius/Sylius/issues/2776) -- concurrency pitfall validation
- [BAZU Telegram Mini Apps E-Commerce Guide](https://bazucompany.com/blog/creating-an-online-store-with-telegram-mini-apps-a-comprehensive-guide/)

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
