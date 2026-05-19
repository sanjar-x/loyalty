# Sprint 3 part 2 — Frontend Tracker

Branch: `feat/sprint3-part2` (off main `c788adb` — Sprint 3 part 1 merged).
OpenAPI snapshot: post-Sprint-3 final (D0.1 + D0.3 + D1.2). LOG-003 list endpoint
**ещё не в snapshot** — Backend hotfix параллельно.

## Phases

### A2 — Catch-up (non-blocking, можно делать сразу)

| ID   | Task                                                       | Status | Notes                                                                                                |
| ---- | ---------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------- |
| A5.1 | recipientSnapshot block в OrderDetailsView с маскированием | done   | post-D0.1, 28 unit+integration tests                                                                 |
| A5.2 | Real HoldReason + grouped CancellationReason в modals      | done   | post-D0.1, BFF \_meta route, useCancellationReasons (30m staleTime), 7 modal tests                   |
| A6   | ETag verify smoke test для Recipient                       | done   | post-D0.3, 2 smoke tests, Sprint-4 marker added in etag-store.js                                     |
| A3.2 | Attributes 3-tab admin                                     | done   | 12 BFF routes, 3 entity slices, 5-modal form feature, 3-tab page, 18 tests                           |
| A3.3 | Templates admin с DnD bindings                             | done   | 6 BFF routes, entity slice (templates+bindings), 5-modal feature, DnD + Alt+↑↓, list+detail, 8 tests |

### B — Logistics shipments admin UI (blocked on Backend LOG-003)

| ID  | Task                                | Status  | Notes                                       |
| --- | ----------------------------------- | ------- | ------------------------------------------- |
| B1  | entities/shipment slice             | blocked | requires GET /admin/logistics/shipments     |
| B2  | features/shipment-actions slice     | blocked | depends on B1                               |
| B3  | admin/shipments list + detail pages | blocked | depends on B1, B2                           |
| B4  | Order detail cross-links            | blocked | depends on B1                               |
| B5  | Conditional polling tracking events | blocked | depends on B1                               |
| B6  | Booking pending UX (post-D1.2)      | pending | `booking_failed` есть в HoldReason snapshot |

### C — Pre-launch UX polish (после A2 + B)

| ID  | Task                | Status  | Notes                        |
| --- | ------------------- | ------- | ---------------------------- |
| C1  | Accessibility audit | pending | docs/sprint-3-a11y-audit.md  |
| C2  | Performance audit   | pending | docs/sprint-3-perf-audit.md  |
| C4  | I18n review         | pending | docs/sprint-3-i18n-review.md |

## Pipeline

```
[Frontend A2: A5.1 → A5.2 → A6 → A3.2 → A3.3]   (~3-4h)
        ‖
[Backend hotfix: LOG-003 list endpoint]           (~1-2h)
        ↓ (after both)
[Frontend B1 → B2 → B3 → B4/B5/B6 параллельно]
        ↓
[Frontend C1 || C2 || C4]
        ↓
[PR feat(admin): Sprint 3 part 2]
```

## Definition of Done

- npm run lint clean (max-warnings=0)
- npm run typecheck clean
- npm test passes (~450+ tests)
- npm run format:check clean
- All TODO(backend-gap) → resolved (A5) or renamed TODO(sprint-4) с явной ссылкой на backend deferred doc
- PR open с smoke testing checklist

## Logbook

- 2026-05-09 22:58 — pre-flight done: pulled main `c788adb`, branch `feat/sprint3-part2` created, snapshot verified.
- 2026-05-09 23:08 — A5.1 done: PII masking helpers + RecipientSnapshotPanel + integration test. 414/414 vitest, lint/typecheck clean.
- 2026-05-09 23:25 — A5.2 done: typed HoldReason / CancellationReason. New BFF route `_meta/cancellation-reasons`, hook `useCancellationReasons` (30 min staleTime), HoldResumeModal radiogroup (4 admin-pickable values), ForceCancelModal grouped picker with ru/code search. 421/421 vitest.
- 2026-05-09 23:29 — A6 done: ETag/If-Match smoke test for Recipient (GET → cache → PATCH replay → 412 → invalidate). TODO(sprint-4) anchor added in `etag-store.js`. 423/423 vitest.
- 2026-05-10 01:36 — A3.2 done: Attributes 3-tab admin (Атрибуты / Группы / Значения). 12 BFF routes (incl. `/usage`, `/bulk`, `/values/(de)activate`, `/values/reorder`), 3 entity slices (`attribute` / `attribute-group` / `attribute-value`) with optimistic activate/deactivate, `attribute-form` feature with 5 modals (Attribute / Group / Value / Bulk-CSV / DeleteWithUsage), settings nav entry. 441/441 vitest.
- 2026-05-10 01:44 — A3.3 done: Templates admin. 6 BFF routes (template CRUD + clone + binding CRUD + reorder), `attribute-template` entity slice (templates + bindings + 8 hooks), `attribute-template-form` feature (TemplateForm / BindingsList with HTML5 DnD + Alt+↑↓ keyboard / AddBinding / Clone / AssignToCategory many-to-many fan-out), list + detail pages, settings nav entry. 449/449 vitest.
