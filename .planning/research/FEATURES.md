# Feature Research

**Domain:** Cross-border e-commerce order lifecycle for a marketplace aggregator (Poizon/Taobao/1688 + local Russian suppliers)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

#### Cart (Customer-Facing)

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| Unified cart (all sources mixed) | Core platform value -- customer shouldn't know product origins | MEDIUM | Cart already has a `useCart` stub with the right interface (id, name, price, quantity, size, image). Backend must persist cart server-side, keyed to user identity. localStorage-only cart loses data across devices and after Telegram cache clears |
| Add to cart with size/variant pre-selected | Every apparel e-commerce app does this; sneaker/streetwear customers expect size selection before cart add | LOW | Product page already renders variants. Cart item needs `sku_id` (not just `product_id`) to capture the exact variant |
| Quantity adjustment in cart | Users buy multiples of the same item; missing this forces remove+re-add | LOW | Already in `useCart` interface (`setQuantity`). Just needs backend backing |
| Remove item from cart | Table stakes -- no explanation needed | LOW | Already in `useCart` interface (`removeItem`, `removeMany`) |
| Cart item count badge on navigation | Users expect visual feedback of cart contents at all times | LOW | Telegram Mini Apps support bottom nav bar; badge on cart icon shows item count |
| Cart persistence across sessions | If user closes Telegram and reopens, cart must survive. localStorage is unreliable in Telegram WebApps (cache may be cleared) | MEDIUM | Server-side cart persistence is necessary. Cart should be a backend resource, not just frontend state |
| Line item price display in RUB | Prices are set manually in RUB -- customer sees final ruble price, never yuan | LOW | Already the pricing model per PROJECT.md |

#### Checkout (Customer-Facing)

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| Checkout summary with item list, sizes, prices | Every e-commerce checkout shows what you're buying | LOW | Existing checkout page already renders grouped items with size, article, price. Needs to pull from real cart API |
| Delivery address input (free text) | Users must tell platform where to ship | LOW | PROJECT.md explicitly scopes this as free text field. No PVZ API integration needed yet |
| Recipient info (name, phone, email) | Required for delivery and cross-border customs. Russian customs law requires real recipient data for international parcels | MEDIUM | Existing checkout page already has recipient modal with FIO, phone (+7 format), email. Needs backend persistence per order, not just localStorage |
| Customs data collection (passport, INN) for cross-border items | Russian customs (FTS Order 1060) requires passport series/number, issue date, birth date, INN for international parcels | MEDIUM | Existing checkout page already has customs data modal. Only required when order contains items from Chinese sources. Must be stored securely |
| Order total calculation (subtotal + delivery estimate) | Users need to know final cost before confirming | LOW | Existing checkout calculates subtotal. Delivery pricing is "from 99 RUB" as placeholder -- acceptable for MVP with manual pricing |
| Order placement confirmation | User clicks "place order" and sees confirmation that order was created | LOW | Simple confirmation screen/modal after successful POST to backend |
| Pre-filled data from Telegram identity | Telegram provides name and sometimes phone -- use it to reduce friction | LOW | `identity` module already handles Telegram auth. Pre-fill recipient name from Telegram profile data |

#### Order Tracking (Customer-Facing)

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| Order list in profile | Users need to see their order history. Every e-commerce app has "My Orders" | LOW | Customer frontend already has `/profile/orders` page with `OrdersClient.tsx` -- currently renders empty array. Needs real API |
| Order detail view with items and status | Clicking an order shows what's in it and current state | MEDIUM | Frontend already has `/profile/orders/[id]` with status-specific views (in-transit, pickup, received, cancelled). Needs real data |
| Basic status display (placed, in transit, at pickup, received, cancelled) | Users need to know where their order is. These 5 states match the existing frontend design | LOW | Status labels already defined in frontend constants: placed, in_transit, pickup_point, received, canceled |
| Order number visible and copyable | Users share order numbers with support | LOW | Already implemented in admin frontend with `CopyMark` component |

#### Admin Order Management

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| Order list with status filtering | Admin needs to see orders grouped by state (placed, in transit, at pickup, cancelled, received) | LOW | Admin frontend already has full UI: `StatusTabs`, `OrderFilters`, `ReasonFilters`, `OrdersList` -- all using seed data. Replace seed with API |
| Order detail view (items, customer, address, totals) | Admin needs full order context to handle fulfillment | LOW | `OrderDetailsView` already renders customer info, pickup address, customs data, item list with per-item status, totals breakdown. Replace hardcoded data with API |
| Per-item status management | Cross-border orders may have items from different sources; each item can progress independently (one item ships from China, another from local supplier) | MEDIUM | `OrderStatusModal` already implements per-item status dropdown (Placed/In Transit/Cancelled) with Chinese track number input per item. This is the core admin workflow |
| Search by order number | Admin needs to find specific orders quickly | LOW | Already in `useOrderFilters` hook -- searches by `orderNumber` |
| Date range filtering | Admin needs to see orders within a time period for reporting | LOW | Already in `useOrderFilters` with `dateRange` state and dayjs filtering |
| Sort by date (newest/oldest) | Basic data table functionality | LOW | Already in `useOrderFilters` with `sortBy` state |
| Top metrics dashboard (order counts, totals) | Admin needs quick overview of business state | LOW | `TopMetrics` component exists in admin, renders against date-filtered orders |
| Source attribution badge (from China / local) | Admin must know which orders involve cross-border logistics vs local fulfillment | LOW | Already rendered as "Iz Kitaya" badge in `OrderCard` and `OrderDetailsView` based on `fromChina` flag |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Telegram bot order notifications | Push notification via Telegram when order status changes -- users are already in Telegram, so notification delivery is near-100%. Other platforms require SMS (costs money) or email (low open rate) | MEDIUM | PROJECT.md lists this as nice-to-have. Bot service already exists. Event system (Transactional Outbox + RabbitMQ) can trigger bot messages on order state transitions |
| Seamless cross-border/local mix in one order | Customer adds a Poizon sneaker and a local-supplier hoodie to same cart and checks out once. Platform handles the split fulfillment invisibly. Most Russian Poizon resellers are single-source shops | HIGH | This is the core platform value per PROJECT.md. Backend must support an order containing items from multiple supplier sources, with potentially different fulfillment timelines. Admin sees per-item source and can manage each independently |
| Admin status pipeline with drag-and-drop | Kanban-style board where admin drags orders between status columns. More intuitive than list view for small teams managing 50-200 daily orders | MEDIUM | Not in current UI. Would be a v2 enhancement. Current list-with-tabs approach is functional for MVP |
| Order history audit log | Every status change, admin action, and timestamp recorded. Valuable for customer disputes and operational review | MEDIUM | Standard in professional OMS. Implement as append-only event log on order aggregate. "Order History" button already exists in admin detail view (currently non-functional) |
| Customer-facing order tracking timeline | Visual step-by-step progress bar (Ordered -> Purchased from supplier -> In transit to Russia -> Customs -> Delivered to pickup -> Ready for pickup). Cross-border customers are anxious about wait times; a detailed timeline reduces support inquiries | HIGH | Not in current milestone scope but high value. Requires tracking granular internal states beyond the 5 customer-facing statuses. Design internal state machine with more states than exposed externally |
| Smart checkout prefill (remember last recipient/address) | Returning customers don't re-enter recipient and address. Existing checkout already reads/writes localStorage for this. Backend persistence would make it cross-device | LOW | Checkout page already implements localStorage-based recipient memory. Could promote to user profile data on backend |
| Admin notes/comments on orders | Admin can attach internal notes to orders (e.g., "waiting for supplier response", "customs issue resolved") | LOW | Simple text field append to order. High operational value for team communication |
| Cancellation reason tracking | When admin cancels an order or item, record why (not for sale, customs rejection, customer request, etc.) | LOW | Admin frontend already has reason filters: not_for_sale, release_refusal, storage_expired. Backend needs to persist cancellation reason per item |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|-------------|-----------------|-------------|
| Real-time inventory/stock tracking | "Show if item is in stock" | This is a dropshipping aggregator -- there is no inventory. Poizon/Taobao/1688 stock is dynamic and unparseable in real-time. Showing "in stock" creates false promises when marketplace items might sell out between browse and purchase | Show estimated availability instead ("usually available"). Let admin mark products as temporarily unavailable. Handle stock-out as a cancellation reason post-order |
| Automated price sync from Chinese marketplaces | "Auto-update prices from Poizon/Taobao" | Exchange rates fluctuate, marketplace prices change without notice, scraping is legally grey and technically fragile. Automated pricing creates margin risk and compliance headaches | Admin sets manual RUB prices (current model). This is correct for early stage. Automated pricing is a future milestone with proper API partnerships |
| Payment gateway integration in this milestone | "Let users pay in-app" | Adds massive complexity: PCI compliance considerations, payment provider integration, refund flows, failed payment handling, split payment edge cases. Offline payment (bank transfer) works for early volume | Create order as `pending_payment`. Admin confirms payment manually. Gateway integration is explicitly out of scope per PROJECT.md |
| Full logistics API integration (CDEK/Pochta/Yandex) | "Auto-track via carrier APIs" | Each carrier API has different authentication, webhook formats, status mappings, and rate-limiting. Integrating 3 carriers simultaneously delays the order management core | Admin enters tracking info manually. Customer sees status as updated by admin. Logistics APIs are a separate future milestone per PROJECT.md |
| Customer self-service order cancellation | "Let customers cancel orders themselves" | Cross-border orders involve purchasing from Chinese marketplaces -- once placed with the supplier, the item may already be bought or shipped. Self-service cancellation creates impossible refund scenarios | Customer requests cancellation via Telegram chat. Admin evaluates whether cancellation is possible based on fulfillment stage, then manually cancels if feasible |
| Multi-currency display (show CNY + RUB) | "Show original Chinese price" | Reveals margin to customer. Creates confusion with fluctuating exchange rates. Customers may try to calculate "real" price and feel overcharged | Show only RUB prices. The platform's value is abstracting away the cross-border complexity, including pricing. Admin sees supplier cost internally |
| Complex discount/promocode engine | "Build a full promotion system" | Discount rules interact with shipping, per-item vs per-order, stacking rules, etc. Engineering effort is disproportionate to early-stage value | Defer to future milestone per PROJECT.md. If needed urgently, simple fixed-amount discount applied at order level only |
| Real-time chat within order details | "Let customer and admin chat about specific orders" | Requires WebSocket infrastructure, message persistence, notification routing, unread counts. Telegram itself is already the communication channel | Use Telegram chat for customer support. Admin can link to Telegram conversation from order. The Telegram bot already exists |

## Feature Dependencies

```
[Product Catalog (existing)]
    |
    v
[Cart Backend] ----requires----> [User Identity (existing)]
    |                                  |
    v                                  v
[Checkout Flow] ----requires----> [Geo/Address (existing, for suggestions)]
    |
    v
[Order Creation] ----requires----> [Supplier Attribution (existing)]
    |
    v
[Order State Machine]
    |
    +---> [Admin Order List + Filters]
    |         |
    |         v
    |     [Admin Order Detail]
    |         |
    |         v
    |     [Admin Per-Item Status Management]
    |
    +---> [Customer Order List]
    |         |
    |         v
    |     [Customer Order Detail]
    |
    +---> [Order Events / History Log] --enhances--> [Telegram Bot Notifications]
```

### Dependency Notes

- **Cart Backend requires User Identity:** Cart must be associated with an authenticated user. Identity module already provides JWT-based user identification.
- **Checkout Flow requires Cart Backend:** Cannot create an order without items in cart.
- **Order Creation requires Supplier Attribution:** Each order item must reference which supplier/marketplace source it comes from, so admin knows fulfillment routing. Supplier module already exists.
- **Admin Per-Item Status Management requires Order State Machine:** Status transitions must be validated against allowed state transitions.
- **Order Events enhances Telegram Bot Notifications:** Event-sourced status changes can trigger bot messages, but notifications are not required for order management to function.
- **Customer Order Detail requires Order State Machine:** Customer view maps internal states to simplified customer-facing statuses.

## MVP Definition

### Launch With (v1) -- This Milestone

Minimum viable order lifecycle -- what's needed to take and manage orders.

- [x] **Cart backend** (server-side persistence, CRUD, user-scoped) -- Foundation for checkout
- [x] **Cart frontend integration** (replace `useCart` stub with real RTK Query hooks) -- Enables add-to-cart flow
- [x] **Checkout flow** (collect recipient, address, customs data for cross-border items, create order) -- Enables order placement
- [x] **Order creation** (persist order with items, customer info, supplier source, delivery info) -- Core data model
- [x] **Order state machine** (5 states: pending_payment, placed, in_transit, pickup_point, received + cancelled) -- Enable status tracking
- [x] **Admin order list** (replace seed data with real API, maintain existing filter/search/sort UX) -- Admin can see orders
- [x] **Admin order detail** (replace hardcoded data with real API, customer info, items, totals) -- Admin can inspect orders
- [x] **Admin per-item status update** (change individual item statuses, add Chinese track numbers) -- Admin can manage fulfillment
- [x] **Customer order list** (replace empty array with real API in `/profile/orders`) -- Customer can see their orders
- [x] **Customer order detail** (basic view with items, status, totals) -- Customer can check order status

### Add After Validation (v1.x)

Features to add once the core order flow is proven with real customers.

- [ ] **Telegram bot notifications on status changes** -- Add when order volume shows customers are checking app for updates (trigger: >10 support inquiries/day about order status)
- [ ] **Order history audit log** -- Add when multiple admins manage orders or customer disputes arise (trigger: >1 admin, or first dispute)
- [ ] **Admin order notes/comments** -- Add when team grows beyond solo operator (trigger: second team member)
- [ ] **Cancellation reason persistence** -- Add when data is needed to identify fulfillment problems (trigger: cancellation rate >10%)
- [ ] **Smart checkout prefill from user profile (backend-backed)** -- Add when repeat purchase rate is measurable (trigger: >20% repeat customers)
- [ ] **Customer-facing order tracking timeline** -- Add when cross-border order anxiety causes support load (trigger: >30% of support inquiries are "where is my order?")

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Payment gateway integration** -- Defer until order volume justifies gateway costs and PCI scope
- [ ] **Logistics API integration (CDEK, Yandex Delivery, Pochta)** -- Defer until manual tracking becomes operationally unsustainable
- [ ] **PVZ pickup point selection via API** -- Defer until logistics APIs are integrated
- [ ] **Automated pricing with currency conversion** -- Defer until supplier API partnerships are formalized
- [ ] **Admin kanban board view** -- Defer until list view becomes unwieldy (>200 orders/day)
- [ ] **Favorites/wishlist integration with cart** -- Defer per PROJECT.md
- [ ] **Promocode/discount engine** -- Defer per PROJECT.md
- [ ] **Customer self-service returns** -- Defer until return policy is formalized

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|-----------|-------------------|----------|
| Cart backend + frontend integration | HIGH | MEDIUM | P1 |
| Checkout flow with order creation | HIGH | MEDIUM | P1 |
| Order state machine (5 states) | HIGH | MEDIUM | P1 |
| Admin order list (real API) | HIGH | LOW | P1 |
| Admin order detail (real API) | HIGH | LOW | P1 |
| Admin per-item status management | HIGH | MEDIUM | P1 |
| Customer order list (real API) | HIGH | LOW | P1 |
| Customer order detail (basic) | MEDIUM | LOW | P1 |
| Telegram bot notifications | MEDIUM | MEDIUM | P2 |
| Order history audit log | MEDIUM | MEDIUM | P2 |
| Admin notes on orders | LOW | LOW | P2 |
| Cancellation reason tracking | MEDIUM | LOW | P2 |
| Checkout prefill from backend | LOW | LOW | P3 |
| Customer tracking timeline | HIGH | HIGH | P3 |
| Payment gateway | HIGH | HIGH | P3 |
| Logistics API integration | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for this milestone -- order lifecycle cannot function without it
- P2: Should have, add when operational needs demand it
- P3: Nice to have, future milestone territory

## Competitor Feature Analysis

| Feature | Poizon Resellers (VK/Telegram shops) | Ozon/Wildberries (Russian marketplaces) | Our Approach |
|---------|--------------------------------------|----------------------------------------|-------------|
| Cart | Usually none -- "DM to order" | Full cart with multi-seller support | Unified server-side cart mixing all sources transparently |
| Checkout | Manual via chat messages | Multi-step with address book, saved cards, PVZ selection | Streamlined single-page checkout in Telegram Mini App. Free text address for now, PVZ selection later |
| Order tracking | Manual updates via Telegram chat | Real-time with carrier API tracking, maps, ETA | Admin-managed status updates visible to customer. Manual but structured -- better than chat-based tracking |
| Payment | Bank transfer with screenshot proof | Online payment with multiple methods | Order created as pending_payment, confirmed offline. Gateway integration future milestone |
| Customs data | Collected ad-hoc via chat | Not applicable (domestic) | Structured customs data form at checkout for cross-border items, stored securely |
| Multi-source fulfillment | N/A (single source) | Separate orders per seller | One order, multiple items from different sources. Admin manages per-item status independently. Customer sees one unified order |
| Admin management | Spreadsheets or no system | Full OMS with automation | Purpose-built admin panel with status tabs, per-item management, Chinese track numbers, source badges |

## Order State Machine Design Notes

The existing frontend already defines 5 statuses: `placed`, `in_transit`, `pickup_point`, `canceled`, `received`.

**Recommended backend state machine (internal, more granular):**

```
pending_payment --> placed --> processing --> in_transit --> at_pickup --> received
                      |           |              |            |
                      v           v              v            v
                   cancelled   cancelled      cancelled    cancelled
```

**Internal states (backend):**
- `pending_payment` -- Order created, awaiting payment confirmation
- `placed` -- Payment confirmed, order accepted
- `processing` -- Admin is procuring from supplier (buying from Poizon/Taobao/1688 or local supplier)
- `in_transit` -- Shipped, moving toward customer
- `at_pickup` -- Arrived at pickup point, awaiting customer collection
- `received` -- Customer confirmed receipt
- `cancelled` -- Terminated at any pre-receipt stage

**Customer-facing status mapping:**
- `pending_payment` --> "Ожидает оплаты"
- `placed` / `processing` --> "Оформлен" (customer doesn't need to know about internal procurement)
- `in_transit` --> "В пути"
- `at_pickup` --> "В пункте выдачи"
- `received` --> "Получен"
- `cancelled` --> "Отменён"

This allows the backend to have richer state transitions for admin/operational use while presenting a simple 5-status view to customers, matching the existing frontend design.

**Per-item vs per-order status:** The admin UI already supports per-item status management (via `OrderStatusModal`). The backend should track status at the item level, with the order-level status derived as an aggregate (using logic similar to the existing `resolveOrderStatus` function in `frontend/admin/src/lib/orders.js`).

## Sources

- Baymard Institute Checkout UX Research 2025: https://baymard.com/blog/current-state-of-checkout-ux
- ArchiMetric UML State Machine for E-Commerce: https://www.archimetric.com/case-study-uml-state-machine-diagram-for-e-commerce-order-lifecycle/
- commercetools State Machine Documentation: https://docs.commercetools.com/learning-model-your-business-structure/state-machines/state-machines-page
- WeSupply Split Shipment Tracking Guide: https://wesupplylabs.com/the-best-guide-to-unified-tracking-for-split-or-multi-shipment-orders/
- BAZU Telegram Mini Apps E-Commerce Guide: https://bazucompany.com/blog/creating-an-online-store-with-telegram-mini-apps-a-comprehensive-guide/
- Poizon International Shipping & Tracking: https://www.poizon.com/trends/international-shipping-and-tracking
- Trafiki Shopping Cart UX Guide 2026: https://www.trafiki-ecommerce.com/marketing-knowledge-hub/the-ultimate-guide-to-shopping-cart-ux/
- Ryviu Managing Split Orders Across Suppliers: https://www.ryviu.com/blog/manage-split-orders
- Existing codebase analysis: admin seed data, checkout page, order components, useCart stub, constants

---
*Feature research for: Cross-border e-commerce order lifecycle*
*Researched: 2026-03-28*
