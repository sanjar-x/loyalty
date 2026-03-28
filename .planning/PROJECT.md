# Loyality — EAV Catalog Hardening

## What This Is

A hybrid e-commerce platform combining traditional online retail with cross-border marketplace aggregation (Poizon, Taobao, Pinduoduo, 1688). Customers buy from Chinese marketplaces and local/Russian suppliers in one unified storefront, with orders delivered to local pickup points (PVZ) via dropshipping logistics partners.

The backend is a DDD modular monolith (Python/FastAPI/SQLAlchemy/PostgreSQL) with hexagonal architecture. This milestone focuses exclusively on hardening the existing EAV Catalog module — analyzing it for correctness, achieving comprehensive test coverage, validating API contracts and data integrity, fixing discovered issues, and making the catalog production-ready as the foundation for the upcoming order system.

## Core Value

The EAV Catalog module must be provably correct and thoroughly tested — it is the foundation for cart, checkout, and order management. Every SKU, price, variant, and attribute must be reliable before building on top of it.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. Inferred from existing codebase. -->

- ✓ Brand CRUD with slug generation and i18n support — existing
- ✓ Category management with nested tree structure — existing
- ✓ Attribute templates and template-to-category bindings — existing
- ✓ Attribute groups for organizing product attributes — existing
- ✓ Product creation with EAV attribute system — existing
- ✓ Product variants with attribute values — existing
- ✓ SKU management with pricing and stock tracking — existing
- ✓ SKU matrix generation from variant combinations — existing
- ✓ Product status FSM (draft → active → archived) — existing
- ✓ Product media management via image backend integration — existing
- ✓ Storefront product listing query — existing
- ✓ RBAC-protected admin catalog endpoints — existing

### Active

<!-- Current scope. Building toward these. -->

- [ ] EAV domain model analysis — validate correctness of entity relationships, aggregate boundaries, and business rules
- [ ] Comprehensive unit tests for all catalog command handlers (44 of 46 currently untested)
- [ ] Comprehensive unit tests for all catalog query handlers
- [ ] Integration tests for catalog repositories (CRUD operations, complex queries)
- [ ] Integration tests for catalog API endpoints (request/response contracts)
- [ ] Data integrity validation — schema constraints, migrations, FK relationships
- [ ] Fix bugs and logic errors discovered during analysis and testing
- [ ] API contract documentation — validate all catalog endpoints against expected behavior
- [ ] Performance validation — query patterns, N+1 detection, pagination efficiency
- [ ] Entity file refactoring — split 2,220-line god-class into separate domain files

### Out of Scope

- Order module / cart / checkout backend — future milestone, depends on this one
- Payment integration — future milestone
- Frontend changes — this milestone is backend catalog only
- Other module testing (identity, user, geo) — separate effort
- Refactoring away from EAV pattern — EAV is a deliberate architectural choice
- Search/filtering backend for storefront — future milestone
- Admin frontend fixes (mock data, TypeScript migration) — separate effort

## Context

- **Existing codebase:** DDD modular monolith with 5 modules (catalog, identity, user, geo, supplier)
- **Catalog module size:** 21,853 LOC source, 796 LOC tests (1.1% test-to-source ratio — worst in codebase)
- **Entity god-class:** `backend/src/modules/catalog/domain/entities.py` is 2,220 lines with 9+ entity/aggregate classes
- **Untested commands:** 44 of 46 command handlers have zero test coverage
- **Architecture:** Hexagonal (ports & adapters) with CQRS — commands use domain + UoW, queries bypass domain
- **Test infrastructure:** pytest + pytest-asyncio + testcontainers (PostgreSQL, Redis, RabbitMQ) already configured
- **Buying model:** Manual buying agent places orders on Chinese marketplaces (no API integrations needed)
- **Deployment:** Railway PaaS, PostgreSQL 18, Redis 8.4, RabbitMQ 4.2.4

## Constraints

- **Keep EAV pattern**: The Entity-Attribute-Value architecture for the catalog is a deliberate design choice — do not refactor away from it
- **Tech stack**: Python 3.14, FastAPI, SQLAlchemy 2.1 (async), PostgreSQL, Dishka DI
- **Architecture**: Must follow existing hexagonal/CQRS patterns — commands through domain, queries direct to ORM
- **Testing**: Use existing test infrastructure (pytest, testcontainers, polyfactory)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Catalog-only milestone before orders | Catalog is foundation for cart/checkout — must be solid first | — Pending |
| Keep EAV pattern | Deliberate architectural choice for flexible product attributes | — Pending |
| Split entity god-class | 2,220 lines in single file hurts maintainability and testability | — Pending |
| Manual buying agent model | No marketplace API integrations needed — human agents order from Poizon/Taobao/etc. | — Pending |

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
