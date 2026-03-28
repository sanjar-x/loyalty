# Requirements: LoyaltyMarket Order Lifecycle

**Defined:** 2026-03-28
**Core Value:** Customer can place an order from any product source and the platform handles fulfillment invisibly

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Infrastructure

- [ ] **INFRA-01**: Outbox relay must not silently consume unknown event types — unhandled events remain unprocessed for later retry

### Cart

- [ ] **CART-01**: Customer can add a product SKU to their cart from the product page
- [ ] **CART-02**: Customer can view their cart with all added items, quantities, and current prices
- [ ] **CART-03**: Customer can update item quantity in the cart
- [ ] **CART-04**: Customer can remove an item from the cart
- [ ] **CART-05**: Cart persists server-side (Redis) and survives Telegram Mini App session restarts
- [ ] **CART-06**: Cart items are validated against catalog SKUs (unavailable items flagged)
- [ ] **CART-07**: Cart displays current prices (re-enriched from catalog on each view)

### Checkout

- [ ] **CHKOUT-01**: Customer can proceed to checkout from the cart
- [ ] **CHKOUT-02**: Checkout pre-fills customer name and phone from Telegram profile (editable)
- [ ] **CHKOUT-03**: Customer can enter a delivery address as free text
- [ ] **CHKOUT-04**: Customer can add order notes (free text instructions)
- [ ] **CHKOUT-05**: Customer confirms selected size/variant for each item before placing order
- [ ] **CHKOUT-06**: Customer can enter customs data (passport/INN) for cross-border items
- [ ] **CHKOUT-07**: Product data (name, price, image, variant, supplier) is snapshot at order creation time — order remains valid even if products change later

### Order Backend

- [ ] **ORD-01**: Order is created atomically from cart contents (cart cleared on success)
- [ ] **ORD-02**: Order stores full item details as immutable snapshots (no foreign keys to live catalog)
- [ ] **ORD-03**: Each order item has independent status tracking (item-level state machine, not order-level)
- [ ] **ORD-04**: Order status FSM supports core states: pending_payment, confirmed, processing, shipped, delivered, cancelled
- [ ] **ORD-05**: Order status FSM is extensible for future states (warehouse, customs, logistics stages)
- [ ] **ORD-06**: Order records supplier/marketplace source attribution per item
- [ ] **ORD-07**: Order has a human-readable order number for admin/customer reference
- [ ] **ORD-08**: Order status changes are recorded in an audit history with timestamps and optional reason

### Admin

- [ ] **ADM-01**: Admin can view a list of all orders with pagination
- [ ] **ADM-02**: Admin can filter orders by status, date range, and source type (Chinese marketplace vs local supplier)
- [ ] **ADM-03**: Admin can search orders by order number or customer name/phone
- [ ] **ADM-04**: Admin can view full order details: items, customer info, delivery address, supplier source, status timeline
- [ ] **ADM-05**: Admin can manually update status per order item (with reason/notes)
- [ ] **ADM-06**: Admin can assign/reassign supplier or marketplace source to an order item
- [ ] **ADM-07**: Admin can view order analytics: order counts by status, revenue totals, source breakdown

### Customer UI

- [ ] **CUST-01**: Customer can view their order history (list of past and active orders)
- [ ] **CUST-02**: Customer can view order details with item-level status tracking
- [ ] **CUST-03**: Cart page in Telegram Mini App with add, remove, update quantity functionality
- [ ] **CUST-04**: Checkout page in Telegram Mini App connected to real backend (not localStorage)

### Notifications

- [ ] **NOTIF-01**: Customer receives Telegram bot message when an order item status changes
- [ ] **NOTIF-02**: Notification includes order number, item name, and new status in human-readable format

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Payment Integration

- **PAY-01**: Customer can pay for order online via payment gateway (YooKassa/Tinkoff)
- **PAY-02**: Order status automatically transitions on payment confirmation webhook
- **PAY-03**: Refund processing for cancelled/returned orders

### Logistics Integration

- **LOG-01**: PVZ pickup point selection from CDEK/Yandex Delivery/Pochta Russia APIs
- **LOG-02**: Automatic tracking number import from logistics partners
- **LOG-03**: Real-time delivery status sync from logistics APIs

### Dynamic Pricing

- **PRICE-01**: Automatic price parsing from Chinese marketplace listings
- **PRICE-02**: Currency conversion (CNY → RUB) with configurable markup
- **PRICE-03**: Price sync scheduler (periodic re-calculation)

### Social Features

- **FAV-01**: Customer can save products to favorites/wishlist
- **REV-01**: Customer can leave reviews after order completion
- **PROMO-01**: Promocode/discount system at checkout

## Out of Scope

| Feature | Reason |
|---------|--------|
| Payment gateway integration | Orders created as pending_payment, handled offline — gateway in future milestone |
| Logistics API integration (CDEK, Yandex, Pochta) | Admin tracks manually — APIs in future milestone |
| PVZ picker from API | Requires logistics APIs — free text address for now |
| Dynamic pricing / marketplace parsing | Admin sets fixed prices — automation in future milestone |
| Inventory/stock management | Pure dropshipping model — no warehouse |
| Real-time chat / customer support | Out of platform scope for now |
| Multi-currency display | Single currency (RUB) — cross-border pricing deferred |
| Bulk order import | Not needed at current scale |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | — | Pending |
| CART-01 | — | Pending |
| CART-02 | — | Pending |
| CART-03 | — | Pending |
| CART-04 | — | Pending |
| CART-05 | — | Pending |
| CART-06 | — | Pending |
| CART-07 | — | Pending |
| CHKOUT-01 | — | Pending |
| CHKOUT-02 | — | Pending |
| CHKOUT-03 | — | Pending |
| CHKOUT-04 | — | Pending |
| CHKOUT-05 | — | Pending |
| CHKOUT-06 | — | Pending |
| CHKOUT-07 | — | Pending |
| ORD-01 | — | Pending |
| ORD-02 | — | Pending |
| ORD-03 | — | Pending |
| ORD-04 | — | Pending |
| ORD-05 | — | Pending |
| ORD-06 | — | Pending |
| ORD-07 | — | Pending |
| ORD-08 | — | Pending |
| ADM-01 | — | Pending |
| ADM-02 | — | Pending |
| ADM-03 | — | Pending |
| ADM-04 | — | Pending |
| ADM-05 | — | Pending |
| ADM-06 | — | Pending |
| ADM-07 | — | Pending |
| CUST-01 | — | Pending |
| CUST-02 | — | Pending |
| CUST-03 | — | Pending |
| CUST-04 | — | Pending |
| NOTIF-01 | — | Pending |
| NOTIF-02 | — | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 0
- Unmapped: 36 ⚠️

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after initial definition*
