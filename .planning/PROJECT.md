# LoyaltyMarket

## What This Is

A hybrid e-commerce platform combining traditional online retail with cross-border marketplace aggregation (Poizon, Taobao, Pinduoduo, 1688). Operates as an aggregator/dropshipping model — customers buy from Chinese marketplaces and local/Russian suppliers in one unified Telegram Mini App storefront, without dealing with foreign platforms directly.

## Core Value

Customer can place an order from any product source (Chinese marketplace or local supplier) and the platform handles fulfillment invisibly — one storefront, one checkout, one experience.

## Requirements

### Validated

- ✓ Product catalog with brands, categories, attributes, variants, and SKUs — existing (`catalog` module)
- ✓ Telegram-based authentication with JWT sessions — existing (`identity` module)
- ✓ User profile management — existing (`user` module)
- ✓ Geographic data with DaData address integration — existing (`geo` module)
- ✓ Supplier management (local and marketplace sources) — existing (`supplier` module)
- ✓ Media asset management with upload, processing, and CDN delivery — existing (`image_backend` service)
- ✓ Customer-facing Telegram Mini App with catalog browsing — existing (`frontend/main`)
- ✓ Admin panel with product, brand, category, and supplier management — existing (`frontend/admin`)
- ✓ Cross-module event system via Transactional Outbox + RabbitMQ — existing (infrastructure)
- ✓ Architecture boundary enforcement via pytest-archon — existing (test infrastructure)

### Active

- [ ] Shopping cart (unified, mixing items from any source)
- [ ] Checkout flow (contact info pre-filled from Telegram, delivery address text field, order notes, size/variant confirmation)
- [ ] Order creation (persisted with full item details, customer info, and supplier source)
- [ ] Order management admin UI (list with filters, search, full order details view)
- [ ] Order details showing items, customer info, supplier/marketplace source attribution

### Out of Scope

- Payment gateway integration — orders created as `pending_payment`, handled offline for now
- Logistics API integration (CDEK, Yandex Delivery, Pochta Russia) — future milestone
- PVZ pickup point selection from API — customer enters delivery address as free text for now
- Dynamic pricing / marketplace price parsing with currency conversion — admin sets fixed ruble prices manually
- Favorites / wishlist — frontend stub exists, deferred
- Customer reviews — stub exists, deferred
- Promocodes / discount system — deferred
- Order status tracking UI (customer side) — nice-to-have, not required for milestone completion
- Telegram bot notifications on status changes — nice-to-have, not required
- Admin manual status management pipeline — nice-to-have, not required

## Context

**Existing codebase:** DDD modular monolith (Python 3.14 / FastAPI / SQLAlchemy 2.1 / PostgreSQL) with Clean/Hexagonal Architecture, CQRS, and Transactional Outbox pattern. Five bounded contexts exist: `catalog`, `identity`, `user`, `geo`, `supplier`.

**Admin panel gap:** The admin frontend currently uses hardcoded seed data for orders, reviews, staff, promocodes, and referrals. Only brands, categories, and suppliers have real API integration. This milestone replaces the orders seed data with a real backend module and API.

**Frontend architecture:** Customer-facing app is a Telegram Mini App (Next.js 16 / React 19) using RTK Query with BFF proxy pattern. Admin panel is Next.js 16 with plain JavaScript (no TypeScript).

**Deployment:** Docker-based with four deployable units: main backend, image backend, Telegram bot, and two Next.js frontends.

## Constraints

- **Tech stack**: Must follow existing DDD/CQRS/Hexagonal patterns — new `order` module follows same structure as `catalog`, `identity`, etc.
- **Frontend**: Customer app is a Telegram Mini App — must work within Telegram WebApp constraints
- **No warehouse**: Pure dropshipping — no inventory management, stock tracking, or warehouse operations
- **Pricing**: Admin sets prices manually in local currency (RUB) — no automated price calculation
- **Fulfillment**: Manual for this milestone — admin handles supplier communication and logistics tracking outside the platform

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| No payment integration this milestone | Reduces scope; payment handled offline until volume justifies gateway costs | — Pending |
| No logistics API integration this milestone | CDEK/Yandex/Pochta APIs add complexity; admin tracks manually for now | — Pending |
| Simplified order state machine | Start with core states, design for extensibility to handle full multi-stage pipeline later | — Pending |
| Unified cart (not split by source) | Customer shouldn't care where products come from — that's the platform's value | — Pending |
| Free text delivery address (no PVZ picker) | PVZ selection requires logistics APIs not in scope; text field is interim solution | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 after initialization*
