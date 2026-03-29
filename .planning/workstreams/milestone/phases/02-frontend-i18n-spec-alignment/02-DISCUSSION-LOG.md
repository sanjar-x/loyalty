# Phase 2: Frontend i18n & Spec Alignment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 02-frontend-i18n-spec-alignment
**Areas discussed:** Scope i18n-фикса, Spec update подход

---

## Gray Area Selection

Three gray areas were identified:
1. Стратегия en-fallback — **NOT SELECTED** (recorded as Claude's Discretion: copy ru → en)
2. Scope i18n-фикса — **SELECTED**
3. Spec update подход — **SELECTED**

---

## Scope i18n-фикса

| Option | Description | Selected |
|--------|-------------|----------|
| Только product form (Recommended) | Фиксим useProductForm.js — единственное место с i18n dict payload | |
| Продукт + аудит остальных | Фиксим product form + проверяем CategoryModal и BrandSelect | |
| Все write-path формы | Полный аудит всех POST/PATCH в admin на корректность i18n payloads | ✓ |

**User's choice:** Все write-path формы
**Notes:** User wants comprehensive audit of all admin forms that send data to backend, not just product creation. Codebase scan identified CategoryModal (plain `name` string), BrandSelect (plain `name` string), and RoleModal as additional audit targets.

---

## Spec update подход

| Option | Description | Selected |
|--------|-------------|----------|
| Find/replace + примечание (Recommended) | Заменить I18n → I18N, обновить примечание на строке 36-37 | |
| Полный ревью спеки | Кроме I18n→I18N, проверить все JSON-примеры на актуальность (921 строк) | ✓ |
| Не трогать спеку | Спека — справочный документ, реальный контракт — в коде | |

**User's choice:** Полный ревью спеки
**Notes:** User wants a full review of product-creation-flow.md for accuracy against current backend behavior, not just the I18n→I18N naming fix.

---

## Claude's Discretion

- En-fallback strategy: copy ru → en when en field is empty (from ROADMAP success criteria)
- Whether to extract shared i18n helper
- Fix ordering within phase plans

## Deferred Ideas

None — discussion stayed within phase scope.
