# Phase 4: Brand, Category & Attribute Command Handlers - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-03-28
**Phase:** 04-brand-category-attribute-command-handlers
**Areas discussed:** Handler test granularity, Mock vs FakeUoW usage

---

## Handler Test Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| One class per handler | TestCreateBrand, TestUpdateBrand — isolated per use case | ✓ |
| Grouped by entity | TestBrandHandlers — all handlers in one class | |

**User's choice:** One class per handler
**Notes:** Each handler is a separate use case. Grouped-by-entity classes become unreadable at scale.

---

## Mock vs FakeUoW Usage

| Option | Description | Selected |
|--------|-------------|----------|
| FakeUoW for ALL handlers | Consistency, validates real repo interactions | ✓ |
| FakeUoW + AsyncMock mix | FakeUoW for complex, AsyncMock for trivial CRUD | |

**User's choice:** FakeUoW for ALL handlers
**Notes:** Simple AsyncMock "tests nothing real, just confirms the mock was called." FakeUoW validates handler-repo interaction. Consistency > convenience. Even trivial handlers can have bugs in validation, event emission, or error handling.

---

## Claude's Discretion

- Edge case count per handler
- ILogger interaction testing
- Error message vs exception type assertions
- Test method naming style
