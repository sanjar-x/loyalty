# Phase 1: Test Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 01-test-infrastructure
**Areas discussed:** Factory pattern, FakeUoW design, Hypothesis depth, File organization, N+1 detection scope, Cross-module stubs, Test naming style

---

## Factory Pattern Choice

| Option | Description | Selected |
|--------|-------------|----------|
| Builders for all (Recommended) | Fluent Builders for domain entities. Mothers become thin wrappers calling builders with defaults. | ✓ |
| Mothers + Polyfactory | Expand catalog_mothers.py for domain entities, orm_factories.py for ORM models. Skip builders. | |
| All three patterns | Builders for complex entities, Mothers for simple ones, Polyfactory for ORM. | |

**User's choice:** Builders for all
**Notes:** Already proven with CategoryBuilder pattern in existing codebase.

---

## FakeUoW Design

| Option | Description | Selected |
|--------|-------------|----------|
| Full in-memory fake (Recommended) | Real dict-based repositories, tracks registered aggregates, collects domain events on commit. | ✓ |
| Enhanced AsyncMock | Extend existing make_uow() pattern with event collection. Lighter but tests verify mock interactions. | |
| You decide | Claude picks the best approach. | |

**User's choice:** Full in-memory fake
**Notes:** Tests should verify actual state changes, not mock interactions.

---

## Hypothesis Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Leaf entities only (Recommended) | Strategies for value objects and simple entities. Product aggregate too complex for random generation. | |
| Full aggregate trees | Generate complete Product→Variant→SKU hierarchies. High value but complex to build. | ✓ |
| You decide | Claude picks depth based on what's practical. | |

**User's choice:** Full aggregate trees
**Notes:** User wants comprehensive EAV combinatorial coverage.

---

## File Organization

| Option | Description | Selected |
|--------|-------------|----------|
| One file per domain (Recommended) | catalog_builders.py with all catalog Builders. Keeps existing pattern. | |
| One file per entity | product_builder.py, brand_builder.py, etc. More files but easier to find. | ✓ |
| You decide | Claude picks based on entity count and complexity. | |

**User's choice:** One file per entity
**Notes:** Separate files for clarity with 9+ entity types.

---

## N+1 Detection Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Context manager only (Recommended) | assert_query_count context manager. Phases 7-8 use it in their own tests. | |
| Manager + catalog presets | Context manager PLUS pre-built assertions for common catalog query patterns. | ✓ |
| You decide | Claude picks scope. | |

**User's choice:** Manager + catalog presets
**Notes:** Pre-built baselines for catalog queries serve as reference for later phases.

---

## Cross-Module Stubs

| Option | Description | Selected |
|--------|-------------|----------|
| Shared fakes directory (Recommended) | tests/fakes/ with FakeSupplierQueryService, FakeImageBackendClient. Reusable across phases. | |
| Per-test inline mocks | AsyncMock per test function. Simpler but duplicated across 44+ handler tests. | ✓ |
| You decide | Claude picks based on dependency complexity. | |

**User's choice:** Per-test inline mocks
**Notes:** Keep stubs simple and local to each test.

---

## Test Naming Style

| Option | Description | Selected |
|--------|-------------|----------|
| Class per entity (Recommended) | TestBrand, TestProduct, TestSKU classes. Matches identity module pattern. | ✓ |
| Flat functions | test_create_brand_success(), etc. Simpler, no class boilerplate. | |
| You decide | Claude picks based on test count per file. | |

**User's choice:** Class per entity
**Notes:** Consistency with existing identity module test organization.

---

## Claude's Discretion

- Exact Builder API design (method names, chaining style)
- Internal structure of FakeUnitOfWork
- Hypothesis strategy shrinking configuration
- Pytest fixture wrappers for common setups

## Deferred Ideas

None — discussion stayed within phase scope.
