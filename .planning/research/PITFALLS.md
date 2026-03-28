# Pitfalls Research

**Domain:** Cross-border e-commerce order lifecycle (marketplace aggregator, DDD modular monolith)
**Researched:** 2026-03-28
**Confidence:** HIGH (domain-specific, grounded in codebase analysis and industry patterns)

## Critical Pitfalls

### Pitfall 1: Flat State Machine That Cannot Model Multi-Source Fulfillment

**What goes wrong:**
The admin seed data uses a flat, order-level state (`placed -> in_transit -> pickup_point -> received | canceled`). If the real backend replicates this, a single order containing both a local-supplier item (ships in 2 days) and a cross-border item (ships in 14 days) cannot represent that one item is delivered while the other is still clearing customs. The entire order appears "stuck" in an ambiguous intermediate state. Admin operators cannot advance individual line items, and customers see misleading status information.

**Why it happens:**
The seed data in `frontend/admin/src/data/orders.js` and the `resolveOrderStatus()` function in `frontend/admin/src/lib/orders.js` already encode a flat order-level status derived from per-item statuses via string comparison (e.g., `statuses.every(s => s === 'Otmenen')`). Developers naturally replicate this pattern in the backend domain model, treating order status as a single field rather than a composite derived from line-item states.

**How to avoid:**
Design the state machine at the **OrderItem** (or fulfillment-group) level, not the Order level. Each `OrderItem` tracks its own lifecycle: `pending -> confirmed -> sourced -> shipped -> in_transit -> delivered | canceled`. The Order aggregate computes its display status by aggregating child states (e.g., "partially shipped" when some items are shipped and others are not). This is the "sub-order" or "fulfillment group" pattern used by Shopify, WooCommerce, and every marketplace aggregator at scale.

Concretely:
- `Order` has `status` as a **computed property** (no column), derived from its `OrderItem` states.
- `OrderItem` has `status` as a **persisted enum column** with explicit transition rules.
- The admin UI shows per-item status badges, not just an order-level badge.
- Transition commands operate on `OrderItem`, not `Order` (e.g., `MarkItemShipped`, not `MarkOrderShipped`).

**Warning signs:**
- A single `status` column on the `orders` table with no corresponding column on `order_items`.
- Admin status-change endpoint accepts `order_id` + `new_status` without specifying which items.
- The `resolveOrderStatus` function in the frontend grows increasingly complex with special cases.

**Phase to address:**
Phase 1 (Domain modeling) -- this is a foundational design decision that is extremely expensive to change after data exists.

---

### Pitfall 2: Cart-to-Order Price/Product Drift (Missing Snapshot)

**What goes wrong:**
The cart references products by ID, but between adding to cart and placing an order, the admin may change the product's price, deactivate the SKU, or even delete the product. If the order creation command reads the current catalog state, the customer pays a different price than what they saw. Worse, if a product was deleted, the order creation fails entirely or creates an order with broken references.

**Why it happens:**
In a dropshipping model with admin-set prices, price changes are frequent (exchange rates shift, supplier costs change). The codebase has no inventory tracking (PROJECT.md: "No warehouse: Pure dropshipping"), so there is no stock-reservation mechanism that would naturally force a "lock" at cart time. The cart hook (`useCart.ts`) stores only `id`, `price`, `quantity` -- a thin reference, not a snapshot.

**How to avoid:**
Snapshot product data at **two moments**:
1. **Cart addition:** Store `sku_id`, `product_name`, `variant_name`, `price_rub`, `image_url`, and `supplier_id` in the cart item row (server-side cart). Display this cached data in the cart UI.
2. **Order creation:** Re-validate against the catalog. If price changed, warn the user (or reject). Copy all product details into `order_items` as immutable snapshot fields -- the order must be readable even if the product is later deleted.

The `OrderItem` entity must contain: `product_name`, `variant_name`, `sku_code`, `price_at_order_time`, `image_url`, `supplier_id`, `supplier_type` -- none of these should be foreign-key lookups.

**Warning signs:**
- `order_items` table has `product_id` FK but no `product_name` or `price_at_order_time` columns.
- Displaying an order requires joining to the `products` table.
- Deleting a product causes `IntegrityError` on historical orders.

**Phase to address:**
Phase 1 (Domain modeling) for the Order entity design; Phase 2 (Cart implementation) for the server-side cart with snapshot behavior.

---

### Pitfall 3: Client-Side Cart Without Server-Side Persistence

**What goes wrong:**
The current `useCart.ts` is a stub returning an empty array. If the cart is implemented purely in frontend state (localStorage, Redux, React state), the following break: (a) cart contents are lost when the user switches devices or clears browser data, (b) the Telegram Mini App's WebView storage is unreliable and can be cleared by the OS, (c) there is no server-side validation at cart time, so deleted/deactivated products accumulate in the cart, (d) the admin has no visibility into active carts for analytics or debugging.

**Why it happens:**
The checkout page (`frontend/main/app/checkout/page.tsx`) already stores selected IDs, recipient data, customs data, and card info in `localStorage`. This pattern suggests a client-first approach. Developers may continue this pattern for the cart itself, especially since the backend has no cart module yet.

**How to avoid:**
Implement a **server-side cart** in the backend `order` module (or a dedicated `cart` module). The cart is persisted in PostgreSQL, keyed by `user_id`. The frontend calls `POST /cart/items`, `DELETE /cart/items/{id}`, `PATCH /cart/items/{id}` -- standard CRUD. On add, the server validates the SKU exists and is active, snapshots the price, and stores it. The frontend cart hook becomes a thin RTK Query wrapper.

For Telegram Mini App specifically: localStorage persistence is not guaranteed across app restarts on some Android devices. A server-side cart with the user's `identity_id` as the key eliminates this risk entirely.

**Warning signs:**
- Cart data lives only in `localStorage` or React state.
- No `/cart` endpoints in the backend API.
- Users report "my cart was empty when I came back" on Telegram.

**Phase to address:**
Phase 2 (Cart implementation) -- must be server-side from the start.

---

### Pitfall 4: Optimistic Concurrency Missing on Order Status Transitions

**What goes wrong:**
Two admin operators view the same order simultaneously. Operator A changes status from `placed` to `confirmed`. Operator B, still seeing `placed`, changes status to `canceled`. Without optimistic locking, the last write wins -- the order ends up canceled even though it was already confirmed and possibly already communicated to the supplier. This is a classic lost-update problem.

**Why it happens:**
The existing `Supplier` entity uses a `version` field for optimistic locking, but the admin order service (`frontend/admin/src/services/orders.js`) performs in-memory mutations with no concurrency control: `orders = orders.map(...)`. When the real backend is built, developers may forget to add version checking because the prototype never needed it.

**How to avoid:**
- Add a `version: int` field to the `Order` aggregate (following the `Supplier` entity pattern already in the codebase).
- Every state-transition command must include the expected `version`. The repository uses `WHERE id = :id AND version = :expected_version` in the UPDATE.
- On version mismatch, return HTTP 409 Conflict. The admin UI should show "This order was modified by another operator. Please refresh."
- Also enforce **valid transition rules** in the domain: the `OrderItem.transition_to(new_status)` method should raise `InvalidStatusTransitionError` if the transition is not allowed (e.g., `delivered -> placed` is invalid).

**Warning signs:**
- Order entity has no `version` field.
- Status update endpoint accepts only `order_id` + `new_status` (no version).
- Two browser tabs can change the same order's status without conflict detection.

**Phase to address:**
Phase 1 (Domain modeling) for the version field and transition rules; Phase 3 (Admin API) for the HTTP 409 response handling.

---

### Pitfall 5: Cross-Module Coupling Between Order and Catalog

**What goes wrong:**
The `order` module directly imports or depends on `catalog` domain entities, repositories, or query handlers. This violates bounded context boundaries. When the catalog module evolves (e.g., product entity restructuring -- already identified as tech debt in CONCERNS.md with the 2,220-line god-file), the order module breaks. Worse, the order module starts needing catalog's database session, creating transactional coupling.

**Why it happens:**
Order creation needs product information (name, price, image, supplier). The obvious approach is to inject `ProductRepository` into the order creation command handler. The codebase already has `pytest-archon` for architecture boundary enforcement, but it only catches violations if properly configured for the new module.

**How to avoid:**
Follow the DDD integration patterns already established in the codebase (outbox + RabbitMQ):
1. **At order creation time:** The frontend sends the `sku_id` to the order API. The order command handler calls a **Catalog Anti-Corruption Layer** (a thin interface in the order module, e.g., `CatalogReader`) that makes an internal HTTP call or reads from a read-model/cache to get product details. It does NOT import catalog domain entities.
2. **Simpler alternative for this milestone:** Since the order creation endpoint receives data from the frontend (which already has the product details from the catalog API), accept the product snapshot in the request body. The command handler validates `sku_id` exists via a lightweight check, then stores the snapshot.
3. **Add pytest-archon rules** for the new `order` module: `order` must not import from `catalog.domain`, `catalog.application`, or `catalog.infrastructure`.

**Warning signs:**
- `from src.modules.catalog.domain.entities import Product` appearing in order module files.
- Order creation handler injects `ProductRepository`.
- Order and catalog share the same SQLAlchemy session/UnitOfWork instance in a single request.

**Phase to address:**
Phase 1 (Domain modeling) for establishing the anti-corruption layer interface; enforced throughout all phases via pytest-archon rules.

---

### Pitfall 6: Outbox Events Lost for New Order Event Types

**What goes wrong:**
The outbox relay (`backend/src/infrastructure/outbox/relay.py`, lines 137-147) silently marks unknown event types as processed. If the order module emits new domain events (e.g., `OrderCreatedEvent`, `OrderItemStatusChangedEvent`) but the relay handlers are not registered yet, those events are permanently lost -- marked as processed without any handler executing. This is already documented in CONCERNS.md as a known bug.

**Why it happens:**
The relay was built when only catalog events existed and no handlers were wired. The "skip unknown" behavior was a pragmatic choice to prevent the outbox table from growing unboundedly. But for order events (which may trigger Telegram notifications, analytics updates, or future payment webhooks), losing events is unacceptable.

**How to avoid:**
Before deploying the order module:
1. **Fix the relay bug:** Unknown event types should be left unprocessed (remove lines 143-147 that mark them processed), or moved to a dead-letter table. This is a prerequisite, not optional.
2. **Register order event handlers** in the relay before deploying order event producers. Even if the handlers are no-ops initially, they prevent the "silently consumed" behavior.
3. **Add a monitoring query** that alerts when `outbox_messages` has unprocessed events older than N minutes.

**Warning signs:**
- Order events appear in `outbox_messages` with `processed_at IS NOT NULL` but no downstream effect.
- Telegram notifications never fire despite order events being emitted.
- The `outbox_messages` table shows order events being processed in under 1ms (no real handler ran).

**Phase to address:**
Phase 0 (Pre-work / infrastructure fix) -- this must be fixed before the order module ships.

---

### Pitfall 7: Admin UI Replacing Seed Data Without Preserving Filter/UX Contracts

**What goes wrong:**
The admin panel has a sophisticated order filtering system (`useOrderFilters.js`) with status tabs, reason filters, date ranges, and sort modes -- all built against the seed data shape. When the backend API replaces the seed data, the field names, status enums, filter logic, and pagination behavior must exactly match. A mismatch causes silent data loss (e.g., orders not appearing in any tab because their status string does not match any tab's filter).

**Why it happens:**
The seed data uses specific status strings (`placed`, `in_transit`, `pickup_point`, `canceled`, `received`) and a `reasonFilter` field with values (`release_refusal`, `not_for_sale`, `storage_expired`). The admin code does hard string comparisons against these values. If the backend uses different enum names (e.g., `PLACED` vs `placed`, or `awaiting_pickup` vs `pickup_point`), orders fall through every filter.

**How to avoid:**
1. **Document the status contract** between backend API and admin frontend before implementation. The backend enum values must match the strings in `useOrderFilters.js` and the seed data.
2. **Use the seed data as the API response contract:** Write the backend serialization to produce the exact shape that `getOrders()` currently returns (including `orderNumber`, `trackId`, `status`, `fromChina`, `items[].title`, `items[].price`, `items[].size`, etc.).
3. **Replace incrementally:** First, make the API return data in the same shape. Then modify the frontend to use `fetch()` instead of `getOrders()` (following the pattern in `services/brands.js`). Only then evolve the API shape if needed.

**Warning signs:**
- After switching from seed to API, some status tabs show 0 orders.
- The `TopMetrics` component shows different totals than the sum of tab counts.
- Date filtering stops working because the backend returns ISO strings in a different timezone format.

**Phase to address:**
Phase 3 (Admin API integration) -- define the contract in Phase 1, implement in Phase 3.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single `status` column on `orders` table (no per-item status) | Simpler schema, faster initial dev | Cannot model partial fulfillment; requires rewrite when adding logistics APIs | Never -- the platform's core value is multi-source fulfillment |
| Client-side-only cart (localStorage) | No backend work needed for cart | Lost carts on device switch, no validation, no admin visibility, Telegram storage unreliability | Never -- Telegram Mini App storage is unreliable |
| Hardcoded status strings in frontend without a shared enum | No extra abstraction layer | Status rename requires changes in 5+ files, easy to miss one | Only in prototype phase (which is ending) |
| Storing only `sku_id` in order items (no snapshot) | Simpler schema, normalized data | Historical orders break when products change; requires catalog join for every order display | Never for a commerce system |
| Skipping `version` field on Order aggregate | Slightly simpler domain model | Lost updates when multiple admins work simultaneously | Only if single-admin operation is permanently guaranteed |
| Monolithic checkout page (1,645 lines in `checkout/page.tsx`) | All logic in one place for prototyping | Unmaintainable; any change risks breaking unrelated checkout steps; impossible to test | Only during prototype; must be decomposed before adding real order creation |

## Integration Gotchas

Common mistakes when connecting to external services and internal modules.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Catalog -> Order (product data) | Importing catalog domain entities directly into order module | Use an Anti-Corruption Layer: a `CatalogReadService` interface in the order module, implemented by an infrastructure adapter that calls catalog query endpoints or reads a denormalized view |
| Outbox Relay -> Order Events | Deploying order event producers before registering relay handlers | Register handlers (even no-op stubs) before deploying the event-producing code; fix the relay's "mark unknown as processed" bug first |
| Admin Frontend -> Order API | Assuming the API response shape matches the seed data structure | Write an explicit API-to-UI mapper in the service layer; never pass raw API responses directly to components |
| Telegram Mini App -> Backend Cart | Trusting `localStorage` for cart persistence | Always treat client storage as a cache; the server-side cart is the source of truth; sync on app open |
| Checkout Page -> Order Creation | Sending only IDs at checkout (product_id, sku_id) and fetching everything server-side | Send the full snapshot from the frontend for display, but validate server-side; store the validated snapshot in the order |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all orders for admin filtering (current seed pattern: `getOrders()` returns all) | Admin page becomes slow, browser memory spikes | Server-side pagination and filtering from the start; the existing `paginate()` helper supports this | 500+ orders (within first months of operation) |
| COUNT(*) subquery on orders list (existing `pagination.py` pattern) | Admin order list page takes 2-3 seconds on large datasets | For the admin list, the existing pattern is acceptable up to ~50k orders. Add a composite index on `(status, created_at DESC)` to the orders table. Consider cursor-based pagination only if it becomes a bottleneck. | 50k+ orders |
| N+1 query: loading order items for each order in a list | Order list endpoint takes O(n) queries where n = number of orders per page | Use `selectinload(Order.items)` in the SQLAlchemy query for the orders list endpoint. One query for orders, one query for all their items. | Noticeable at 20+ orders per page |
| Unindexed `user_id` on cart table | Cart retrieval slows as user count grows | Add index on `cart_items.user_id` from the start | 10k+ users with active carts |
| Fetching full product details for cart display via catalog API on every cart page load | Cart page is slow, adds load to catalog module | Cache product snapshots in the cart item row; only re-validate on checkout | 50+ concurrent cart viewers |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No rate limiting on order creation endpoint | An attacker or buggy client creates thousands of orders, overwhelming admin workflow and potentially triggering downstream effects (supplier communications) | Add rate limiting per user: max 5 orders per minute. The backend currently has no rate limiting at all (documented in CONCERNS.md). |
| Trusting client-submitted prices in order creation | A malicious user modifies the price in the request body to pay less | Always re-validate price server-side against the catalog at order creation time. The client-submitted price is for display only; the server-side price is authoritative. |
| Exposing supplier details to customers | Cross-border supplier names, IDs, or internal notes leak to the customer-facing API | The customer order API response should contain `source_type: "cross_border" | "local"` and delivery estimates, but never supplier names, IDs, or internal metadata. Admin API is separate. |
| PII in order data without encryption at rest | Customer passport data (passport series, number, INN) from the customs form is stored in plaintext. If the database is breached, all customer identity documents are exposed. | Encrypt PII fields (passport, INN) at the application level before storing. Use a separate encryption key from the database credentials. This is especially critical because Russian customs data includes government-issued identification. |
| Admin order status changes without audit trail | An admin changes an order from `delivered` to `canceled` (to issue a refund), and there is no record of who did it or when | Store every status transition as an `OrderStatusHistory` record: `order_item_id, old_status, new_status, changed_by, changed_at, reason`. This is both a security and a business requirement. |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Admin sees order-level status only, not per-item status | When an order has 3 items from different sources, the admin cannot tell which item is delayed; they must check externally | Show per-item status badges in the order list and detail views. The seed data already has items as an array -- extend each item with its own status. |
| No bulk status update for admin | Admin processes 50 orders daily; changing status one-by-one is tedious | Add a checkbox selection with "Change status for selected" action. This is a table-stakes feature for order management. |
| Customer checkout stores sensitive data (passport, card) in localStorage | Data persists on shared/public devices; violates PCI-DSS spirit; users cannot "log out" of their customs data | Store sensitive form data only in React state (memory). Persist only non-sensitive fields (name, email) in localStorage. Never store full card numbers client-side (the current checkout page stores card last4 + expiry, which is borderline acceptable but full CVV handling is dangerous). |
| No order confirmation screen after checkout | Customer clicks "Pay" and... nothing visible happens (the current checkout page's pay button has an empty `onClick` for non-split payments) | Show an immediate "Order placed" confirmation with order number, then redirect to order details. Use optimistic UI: show confirmation immediately, handle backend errors gracefully. |
| Mixed-source orders show no delivery time differentiation | Customer expects same delivery for all items, but cross-border takes 2-3 weeks while local takes 2-3 days | Group items by delivery timeline in the checkout summary (the frontend already groups by `deliveryText` -- ensure the backend provides meaningful delivery estimates per source type). |
| Admin order detail page is a static view (current `OrderDetailsView` component) | Admin cannot take actions (change status, add notes, contact customer) from the detail page | The detail page should be the primary workspace for order management, with inline status changes, note addition, and action buttons. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Order creation endpoint:** Often missing idempotency key -- verify that double-submitting the checkout form does not create duplicate orders (use a client-generated idempotency token in the request header)
- [ ] **Cart item validation:** Often missing "is this SKU still active?" check -- verify that deactivated/deleted products are removed or flagged when the cart is loaded
- [ ] **Order status transitions:** Often missing "who changed it and why" -- verify that every transition is logged with `admin_id`, `timestamp`, and optional `reason` text
- [ ] **Order total calculation:** Often missing edge cases -- verify behavior when: promo code reduces total below zero, all items are canceled (total should be zero), single item is canceled (total should recalculate)
- [ ] **Admin order list pagination:** Often missing -- verify that the admin fetches pages from the API, not all orders at once (the current seed data pattern loads everything client-side)
- [ ] **Order number generation:** Often using UUID which is unfriendly for phone support -- verify that a human-readable order number is generated (e.g., `LM-20260328-00001`) separate from the internal UUID
- [ ] **Cross-border customs flag:** Often a boolean (`fromChina`) that does not scale -- verify that the source type comes from the supplier entity's `type` field (`CROSS_BORDER` vs `LOCAL`), not a hardcoded boolean
- [ ] **Order event emission:** Often missing -- verify that `OrderCreatedEvent` and `OrderItemStatusChangedEvent` are emitted to the outbox and that relay handlers are registered
- [ ] **Error handling on order creation failure:** Often missing rollback UX -- verify that if order creation fails after the user clicks "Pay", the cart items are preserved (not cleared)

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Flat order-level state machine (no per-item status) | HIGH | Requires database migration to add `status` to `order_items`, backfill existing orders, rewrite all admin status-change logic, and update both frontend apps. Estimated 2-3 sprint disruption. |
| Missing price snapshots in order items | HIGH | Requires migration to add snapshot columns, a backfill script that reads current catalog data (lossy -- historical prices are gone), and audit of all order display code. Historical accuracy is permanently lost. |
| Client-only cart replaced with server-side | MEDIUM | Create the server-side cart table and API. Write a migration path where the frontend checks for localStorage cart data on first load and syncs it to the server. Handle conflicts (item no longer exists). |
| Outbox events lost for order types | HIGH | Lost events cannot be recovered. Must re-emit events for all affected orders by scanning the orders table and creating synthetic events. Downstream consumers must handle idempotent re-processing. |
| Cross-module coupling (order imports catalog) | MEDIUM | Extract an interface, create an infrastructure adapter, update imports. Tedious but mechanical. The pytest-archon rules catch this early if configured. |
| Admin UI status mismatch with backend enums | LOW | Fix the enum mapping in the API serializer or the frontend service layer. Small change, but requires testing every filter tab. |
| No optimistic locking on orders | MEDIUM | Add `version` column with migration (default 1), update repository to use version checks, update all command handlers to pass version. Existing orders get version=1. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Flat state machine (no per-item status) | Phase 1: Domain Modeling | Order entity has `items` collection; each `OrderItem` has its own `status` enum and `transition_to()` method; `Order.status` is a computed property |
| Missing price/product snapshots | Phase 1: Domain Modeling | `OrderItem` entity has `product_name`, `price_at_order_time`, `image_url`, `supplier_id` fields that are not FKs |
| Client-side-only cart | Phase 2: Cart Implementation | Backend has `/cart` endpoints; `useCart.ts` calls the API; no `localStorage` for cart items |
| Missing optimistic locking | Phase 1: Domain Modeling | `Order` has `version` field; status-change command includes `expected_version`; repository UPDATE includes `WHERE version = :v` |
| Cross-module coupling | Phase 1: Domain Modeling | `pytest-archon` rule added: order module cannot import from catalog module; `CatalogReadService` interface defined in order module |
| Outbox relay bug (lost events) | Phase 0: Pre-work | Relay no longer marks unknown event types as processed; monitoring query exists for stale unprocessed events |
| Admin UI/API contract mismatch | Phase 3: Admin Integration | Status enum values documented and tested; integration test verifies API response shape matches frontend expectations |
| Missing audit trail | Phase 1: Domain Modeling | `OrderStatusHistory` entity exists; every `transition_to()` call creates a history record |
| PII exposure (customs data) | Phase 2: Cart/Checkout | Passport and INN fields are encrypted at rest; customer API never returns raw PII |
| No idempotency on order creation | Phase 2: Checkout Flow | Order creation endpoint accepts `Idempotency-Key` header; duplicate requests return the existing order |
| Checkout page monolith (1,645 lines) | Phase 2: Checkout Flow | Checkout page decomposed into `<DeliverySection>`, `<RecipientSection>`, `<CustomsSection>`, `<PaymentSection>`, `<OrderSummary>` components |
| No rate limiting on order creation | Phase 3: Admin/API Hardening | Rate limit middleware applied to `POST /orders` (per-user) |

## Sources

- Codebase analysis: `frontend/admin/src/data/orders.js`, `frontend/admin/src/lib/orders.js`, `frontend/admin/src/hooks/useOrderFilters.js`, `frontend/admin/src/services/orders.js`, `frontend/main/app/checkout/page.tsx`, `frontend/main/components/blocks/cart/useCart.ts`, `backend/src/infrastructure/outbox/relay.py`, `backend/src/modules/supplier/domain/entities.py`, `backend/src/shared/interfaces/entities.py`
- Project documentation: `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`
- [Shopify: How to Manage Split Orders](https://www.shopify.com/blog/split-order) -- sub-order pattern for multi-source fulfillment
- [Spocket: How to Manage Split Orders for Your E-commerce Business](https://www.spocket.co/blogs/how-to-manage-split-orders-for-your-e-commerce-business)
- [SSENSE Tech: DDD Beyond the Basics - Mastering Aggregate Design](https://medium.com/ssense-tech/ddd-beyond-the-basics-mastering-aggregate-design-26591e218c8c) -- aggregate invariants and boundary design
- [SSENSE Tech: Handling Eventual Consistency with Distributed Systems](https://medium.com/ssense-tech/handling-eventual-consistency-with-distributed-system-9235687ea5b3) -- read-after-write pitfalls
- [Sylius: Race conditions in inventory tracking, order, payment status](https://github.com/Sylius/Sylius/issues/2776) -- concurrency bugs in order systems
- [statemachine.app: Common pitfalls to avoid when working with state machines](https://statemachine.app/article/Common_pitfalls_to_avoid_when_working_with_state_machines.html)
- [Fluent Commerce: Enterprise Order Management UX](https://fluentcommerce.com/resources/blog/enterprise-order-management-ux-4-points-to-consider/) -- admin UX considerations
- [commercetools: State machines](https://docs.commercetools.com/learning-model-your-business-structure/state-machines/state-machines-page) -- commercial OMS state machine patterns
- [Medium: How I Eliminated Inventory Race Conditions in a Production E-Commerce System](https://medium.com/@chaturvediinitin/how-i-eliminated-inventory-race-conditions-in-a-production-e-commerce-system-2302ba81846b)
- [Extensiv: Understanding the Challenges in Cross-Border Fulfillment](https://www.extensiv.com/blog/cross-border-fulfillment)

---
*Pitfalls research for: Cross-border e-commerce order lifecycle (LoyaltyMarket)*
*Researched: 2026-03-28*
