# Catalog UX/UI Audit — 2026-05-10

Static pre-launch audit of every catalog-related entry point in the
admin panel (products + brands + categories + attributes + templates).
No real-browser smoke testing — that follows from the Sprint Lead.

> **Phase B status (closed):** every P0 and P1 finding has landed as an
> atomic commit referencing its audit number — see `git log --grep
"audit"` on `feat/sprint3-part2`. P2 and P3 items remain in the
> Sprint 4 / long-term backlog at the bottom of this doc. Reusable
> patterns extracted from the fixes live in
> `docs/catalog-ux-guidelines.md`.

## Summary

| Severity | Description                       | Status             |
| -------- | --------------------------------- | ------------------ |
| **P0**   | Broken UX, blocks user task       | fix immediately    |
| **P1**   | Poor UX, frustrating but workable | fix in this sprint |
| **P2**   | Polish, would improve quality     | Sprint 4 backlog   |
| **P3**   | Nice-to-have                      | long-term backlog  |

| Severity  | Count  | Examples                                                                                                                                                                          |
| --------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0        | **1**  | 7.1 — невидимые но focusable action buttons в `CategoryNode` (keyboard-only пользователь не понимает что есть actions)                                                            |
| P1        | **26** | Loading skeletons / focus trap + return / a11y emoji aria-hidden / banner role="alert" / 412 ETag in `useUpdateProduct` / status badge tone / form aria-invalid / live announcers |
| P2        | **26** | 401 redirect `?next=` / virtualization / bulk-bar role / inline styles / search aria-describedby / 5MB pre-upload validation / cancel-clone toast                                 |
| P3        | **12** | SSE live indicator / arrow icons / sr-only swap / submit pipeline progress (1/8 → 8/8) / illustrations / WCAG-borderline disabled state                                           |
| **Total** | **65** | across 9 pages                                                                                                                                                                    |

Pages audited (9):

1. `/admin/products` — list + filters + bulk
2. `/admin/products/add` — category picker
3. `/admin/products/add/details/[...slug]` — 8-step submit flow
4. `/admin/products/[id]` — detail + actions
5. `/admin/products/[id]/edit` — diff PATCH update
6. `/admin/settings/brands` — CRUD + logo upload
7. `/admin/settings/categories` — tree CRUD
8. `/admin/settings/attributes` — 3-tab CRUD
9. `/admin/settings/attribute-templates` — bindings DnD

Components touched in passing: `~60`.

## Audit dimensions (per page)

- **D1 — Loading states** (initial / pagination / refetch / SSE / long ops)
- **D2 — Error states** (network / 401 / 403 / 404 / 409 / 412 / 422 / 500)
- **D3 — Empty states** (no data / no filter match / pre-action hints)
- **D4 — Optimistic updates** (status change / reorder / toggle / delete / submit)
- **D5 — Accessibility** (keyboard nav / focus visible / focus trap / ARIA / contrast)
- **D6 — Form validation** (required marker / on-blur / slug auto-gen / clamps / pre-upload)
- **D7 — Visual consistency** (toast / spinner sizes / modal sizes / status pills / date / currency)
- **D8 — Performance** (re-renders / lazy modals / image lazy / virtualization / N+1 / SSE cleanup)
- **D9 — i18n** (no hardcoded EN / error_code translations / formatters / pluralization)

---

## /admin/products/[id] — detail + actions

| #    | Severity | Dimension     | Issue                                                                                                           | Fix                                                                                                |
| ---- | -------- | ------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 1.1  | P1       | D1 Loading    | Initial load = `<p>Загрузка…</p>` (page.jsx:271) — generic, нет skeleton, layout shift при рендере              | Render skeleton matching detail layout (header + transition bar + main card + sidebar + SKU table) |
| 1.2  | P1       | D2 Error      | `transitionError` banner (page.jsx:351) без `role="alert"` — screen reader не объявляет                         | Add `role="alert"` + `aria-live="polite"` на errorBanner                                           |
| 1.3  | P1       | D2 Error      | Generic error fallback "Не удалось загрузить продукт" не дискриминирует 403/404/500, не отображает `request_id` | Differentiate by `error.status` (403 / 404 / 500 + request_id)                                     |
| 1.4  | P1       | D5 a11y       | "🚀 Опубликовать" (page.jsx:346) — emoji не помечен `aria-hidden`, screen reader произносит                     | Wrap в `<span aria-hidden="true">🚀</span>`                                                        |
| 1.5  | P1       | D5 a11y       | `Modal` (shared/ui) не имеет focus trap — Tab уходит на фоновую страницу                                        | Focus trap effect в `Modal`: query focusable, Tab/Shift+Tab cycle, autofocus first                 |
| 1.6  | P1       | D5 a11y       | `Modal` не возвращает focus в trigger после close                                                               | В тот же effect — `previousFocus.focus()` при unmount                                              |
| 1.7  | P1       | D7 visual     | `statusBadge` (page.module.css) — единый mute bg для всех 5 статусов; FSM визуально неотличим                   | Добавить status→tone map (draft / enriching / ready_for_review / published / archived)             |
| 1.8  | P2       | D2 Error      | 401 от `apiClient` → `proxy.js` redirect `/login` без `?next=` — после логина detail не восстанавливается       | Sprint 4 backlog — затрагивает auth slice                                                          |
| 1.9  | P2       | D3 Empty      | `SkuPricingTable` empty state не имеет direct CTA-кнопки в `/edit`                                              | Sprint 4 backlog — добавить `<Link href={…/edit}>`                                                 |
| 1.10 | P2       | D4 Optimistic | `transitionMutation` не оптимистический — UI показывает старый статус до refetch                                | Sprint 4 backlog — `onMutate` snapshot + setQueryData                                              |
| 1.11 | P2       | D7 visual     | `formatMoney` локально в `SkuPricingTable.jsx` (RUB/CNY/USD/EUR), `formatCurrency` в shared только RUB — drift  | Sprint 4 backlog — поднять в `shared/lib/utils`                                                    |
| 1.12 | P2       | D8 Perf       | `BulkPurchasePriceModal` импортируется eagerly                                                                  | Sprint 4 backlog — `dynamic()` import                                                              |
| 1.13 | P3       | D1 Loading    | Нет visual indicator SSE подключения                                                                            | Long-term — pulse-dot                                                                              |
| 1.14 | P3       | D5 a11y       | `← Товары` стрелка читается screen reader                                                                       | Long-term — `aria-hidden="true"` на span                                                           |
| 1.15 | P3       | D7 visual     | `disabled:opacity-50` снижает контраст для disabled state (borderline WCAG)                                     | Long-term — explicit disabled style                                                                |

## /admin/products/add/details/[...slug] — 8-step submit

Этот flow в целом хорошо продуман: tab errors, `aria-busy`, validation summary, blocking submit during uploads, autosave, beforeunload guard, polite reorder announcer, Alt+ArrowKey reorder.

| #    | Severity | Dimension  | Issue                                                                                                                                                                                                                                                           | Fix                                                                                                                                                         |
| ---- | -------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.1  | P1       | D5 a11y    | `slugEditButton` (ProductDetailsForm.jsx:777) использует символы `✓` / `✎` в текстовом узле кнопки. Они НЕ обёрнуты `aria-hidden`, screen reader произносит "галочка" / "перо". `aria-label` присутствует, но `<span aria-hidden="true">` всё ещё рекомендуется | Wrap glyphs в `<span aria-hidden="true">`                                                                                                                   |
| 2.2  | P1       | D5 a11y    | На variant-2..N форма «блокируется» через inline `{ pointerEvents: 'none', opacity: 0.6 }` (lines 723–727, 757). Это блокирует клик но НЕ Tab — keyboard-фокус всё ещё попадает в disabled `<input>` без `aria-disabled`                                        | Заменить inline style на проброс `disabled={isNotFirstVariant}` (`<input>` уже его получает) + `aria-disabled` на wrapper для синхронизации со скринридером |
| 2.3  | P1       | D5 a11y    | `<p role="button" tabIndex={0}>` для labels вариантов в validation summary (line 1085) — лучше использовать настоящий `<button>` для семантики и keyboard activation. Сейчас Space НЕ срабатывает (только Enter)                                                | Заменить `<p>` на `<button type="button">` с tabIndex наследованным                                                                                         |
| 2.4  | P1       | D2 Error   | Submit error block (line 1037) — большая ветка `code === ...` повторяет ту же таблицу что в `useEffect` toast (line 323). Drift-prone                                                                                                                           | Извлечь в helper `formatSubmitError(err)` в `model/` и переиспользовать                                                                                     |
| 2.5  | P2       | D5 a11y    | Reorder buttons `◀` `▶` (ImagesSection.jsx:362–372) — символы декоративны, есть `aria-label`. ОК но рекомендуется `<span aria-hidden="true">` для глифа                                                                                                         | Sprint 4 backlog                                                                                                                                            |
| 2.6  | P2       | D6 Form    | `slug` не валидируется on-blur — только after `attempted` flag flips. Пользователь не видит ошибку пока не нажмёт submit                                                                                                                                        | Sprint 4 backlog — добавить onBlur валидацию (стандарт UX)                                                                                                  |
| 2.7  | P2       | D7 visual  | `inline style` для `opacity: 0.6` / `marginTop: -8` / `marginTop: 8` — дрейф с styles module                                                                                                                                                                    | Sprint 4 backlog — extract to module                                                                                                                        |
| 2.8  | P2       | D2 Error   | Error envelope handler в `useEffect` (line 323) автоматически scroll-into-view но не возвращает focus. Screen reader user не понимает что фокус потерял пост-ошибки                                                                                             | Sprint 4 backlog — `errorRef.current?.focus()` + `tabIndex={-1}`                                                                                            |
| 2.9  | P2       | D8 Perf    | `formHasChanges` useMemo с `form.state.variants` в deps — full recompute на любое изменение state. Может быть hot path при typing                                                                                                                               | Sprint 4 backlog — профилирование, может стоит deep-equal cache                                                                                             |
| 2.10 | P3       | D1 Loading | Submit overlay не показывает remaining steps (только current progress text)                                                                                                                                                                                     | Long-term — pipeline indicator (1/8 → 8/8)                                                                                                                  |
| 2.11 | P3       | D5 a11y    | inline `style={{ position: 'absolute', clip: ... }}` (ImagesSection.jsx:228) — visually hidden announcer. Лучше использовать utility `sr-only` Tailwind class                                                                                                   | Long-term — заменить на `className="sr-only"`                                                                                                               |

## /admin/products — list + filters + bulk

| #   | Severity | Dimension     | Issue                                                                                                                                   | Fix                                                              |
| --- | -------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 3.1 | P1       | D1 Loading    | `BulkBar` не получает `bulkActionPending` из `useProductFilters` — actions не disabled во время bulk mutation, double-click → дубликаты | Прокинуть `bulkActionPending` → `disabled` на actions + spinner  |
| 3.2 | P1       | D4 Optimistic | `statusMutation`/`archiveMutation`/`deleteMutation` не optimistic — после клика UI моргает при invalidate→refetch                       | `onMutate` snapshot + `setQueryData` removal; `onError` rollback |
| 3.3 | P2       | D2 Error      | `statusError` auto-clear после 4с — пользователь может не успеть                                                                        | Sprint 4 backlog — 8с + кнопка «Скрыть»                          |
| 3.4 | P2       | D5 a11y       | `BulkBar` (fixed bottom `<div>`) без `role="region"` + `aria-label`                                                                     | Sprint 4 backlog                                                 |
| 3.5 | P2       | D8 Perf       | Список без virtualization (perPage cap=50, при росте критично)                                                                          | Sprint 4 backlog                                                 |
| 3.6 | P2       | D7 visual     | `EmptyResults` без иллюстрации, visual cue слабый                                                                                       | Sprint 4 backlog                                                 |
| 3.7 | P3       | D5 a11y       | searchInput без `aria-describedby` про debounce                                                                                         | Long-term                                                        |
| 3.8 | P3       | D7 visual     | Бейджи `Из Китая`/`Из наличия` без min-height                                                                                           | Long-term                                                        |

## /admin/products/[id]/edit — diff PATCH

Page очень тонкая — основное в `ProductDetailsForm` (см. секцию выше). Findings специфичны для edit + `useUpdateProduct`.

| #   | Severity | Dimension  | Issue                                                                                                                                                                                                                                                           | Fix                                                                                                |
| --- | -------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 4.1 | P1       | D2 Error   | `useUpdateProduct.js:151,253` ловит conflict только через `err.message.includes('409')`/`err.status === 409`. После Sprint 4 (ETag для product/sku) 412 OPTIMISTIC_LOCK_FAILED не будет распознан как conflict — `err.message` локализован, substring "409" нет | Дополнить: `err.status === 409 \|\| err.status === 412 \|\| err.code === 'OPTIMISTIC_LOCK_FAILED'` |
| 4.2 | P1       | D1 Loading | Initial = `<h1>Загрузка…</h1>` — header rendered, body пустой, layout shift при появлении                                                                                                                                                                       | Skeleton matching form layout                                                                      |
| 4.3 | P1       | D2 Error   | Generic fallback `error.message \|\| 'Продукт не найден'` (page.jsx:64) — не дискриминирует 403/404/500, нет request_id                                                                                                                                         | Discriminate (similar to 1.3)                                                                      |
| 4.4 | P2       | D7 visual  | inline `style={{ padding: 24, textAlign: 'center' }}` (page.jsx:62)                                                                                                                                                                                             | Sprint 4 backlog                                                                                   |
| 4.5 | P3       | D5 a11y    | `<h1>Загрузка…</h1>` — H1 для loading state не информативен                                                                                                                                                                                                     | Long-term                                                                                          |

## /admin/products/add — category picker

Чистая навигационная страница, основа уже хорошо сделана: SkeletonColumn loading, recents through localStorage, ARIA labels на back/close/search-clear.

| #   | Severity | Dimension | Issue                                                                                                                                                | Fix                                                                 |
| --- | -------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 5.1 | P2       | D5 a11y   | Search input (page.jsx:286) только с `placeholder`, без `aria-label` — screen reader зачитает label только при наличии attribute                     | Sprint 4 backlog — добавить `aria-label="Поиск категории"`          |
| 5.2 | P2       | D5 a11y   | Search results (`SearchResults`) появляются без `aria-live` — пользователь screen-reader не узнаёт что результаты обновились                         | Sprint 4 backlog — `<div role="region" aria-live="polite">` обёртка |
| 5.3 | P2       | D5 a11y   | Columns + items навигируются как обычные кнопки — для глубоких иерархий `role="tree"` / `role="treeitem"` + `aria-expanded` дали бы лучшую семантику | Sprint 4 backlog                                                    |
| 5.4 | P3       | D3 Empty  | "Категории пока не созданы. Обратитесь к администратору." — без CTA-кнопки в `/admin/settings/categories` (ведь админ может туда пойти)              | Long-term                                                           |

## /admin/settings/brands — CRUD + logo upload

| #   | Severity | Dimension | Issue                                                                                                                                                                                                                               | Fix                                                                |
| --- | -------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 6.1 | P1       | D6 Form   | `BrandFormModal` slug — auto-from-name через `transliterate` (хорошо), но `slug` валидация только при render (border colour, P-text). При первом submit невалидный slug просто блокирует кнопку — нет explicit ошибки в `aria-live` | Добавить `role="alert"` на error text + aria-describedby на input  |
| 6.2 | P1       | D5 a11y   | Logo upload status text меняется (Загрузка/Обработка/Готово/error) — пользователь screen-reader не получает live announcement                                                                                                       | Wrap status `<p>` в `aria-live="polite"`                           |
| 6.3 | P2       | D2 Error  | Logo upload error displayed только inline `<p>` без `role="alert"`                                                                                                                                                                  | Sprint 4 backlog                                                   |
| 6.4 | P2       | D6 Form   | File input `accept="image/*"` принимает все, но описание "JPG / PNG / SVG, до 5 МБ" — нет actual validation 5MB на фронте (полагаемся на backend)                                                                                   | Sprint 4 backlog — клиентская проверка size + format перед reserve |
| 6.5 | P3       | D7 visual | Logo upload — нет progress bar (только статус-текст). Brand logo file = small, но subjectively медленнее без feedback                                                                                                               | Long-term                                                          |

## /admin/settings/categories — tree CRUD

| #   | Severity | Dimension | Issue                                                                                                                                                                                                                     | Fix                                                                                                                  |
| --- | -------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 7.1 | **P0**   | D5 a11y   | `CategoryNode` action buttons (`+ child`, `✎ edit`) скрыты `opacity-0 group-hover:opacity-100`. Они **focusable** через Tab но **визуально невидимы** до hover — keyboard-only пользователь не понимает что есть actions. | Заменить `opacity-0 group-hover:opacity-100` на `focus-within:opacity-100` (или показывать всегда на keyboard-focus) |
| 7.2 | P1       | D5 a11y   | Expand button `▼`/`▶` (CategoryNode) без `aria-label` + `aria-expanded`. Children визуально expand, но screen reader не знает                                                                                             | `<button aria-label="Развернуть" aria-expanded={expanded}>` + `aria-hidden` на glyph                                 |
| 7.3 | P1       | D5 a11y   | Action buttons `+`/`✎` имеют только `title`, нет `aria-label`. Glyph не aria-hidden                                                                                                                                       | `aria-label="Добавить дочернюю"` / `"Редактировать"` + `aria-hidden`                                                 |
| 7.4 | P1       | D2 Error  | `CategoryModal` error block (line 108) без `role="alert"`                                                                                                                                                                 | Add `role="alert"`                                                                                                   |
| 7.5 | P2       | D5 a11y   | Tree без `role="tree"` / `role="treeitem"` — для CTE-иерархии (root → group → leaf) рекомендуется WAI-ARIA tree                                                                                                           | Sprint 4 backlog                                                                                                     |
| 7.6 | P2       | D6 Form   | `CategoryModal` slug — HTML5 `pattern=^[a-z0-9-]+$` показывает только browser-default tooltip (вне UI), нет inline error message                                                                                          | Sprint 4 backlog — кастомный onBlur валидатор                                                                        |

## /admin/settings/attributes — 3-tab CRUD

| #   | Severity | Dimension | Issue                                                                                                                                                                                              | Fix                                                |
| --- | -------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| 8.1 | P1       | D5 a11y   | `AttributeRow` use emoji icons "📚 справочник", "🔎 фильтр" etc. в `<li>` без `aria-hidden`. Screen reader произносит "books emoji справочник"                                                     | Wrap emoji в `<span aria-hidden="true">`           |
| 8.2 | P1       | D2 Error  | `DeleteAttributeConfirmModal` error в `<div role="alert">` ✓, но usage блокировка через `<div role="alert" amber>` — **двойной role="alert"** для одного user-state. Screen reader зачитает дважды | Объединить в один alert или conditional render     |
| 8.3 | P2       | D6 Form   | `AttributeFormModal` validation — onChange shows error text inline через `error` prop, но не `aria-invalid` на `<input>`. Хорошо для глаз, плохо для AT                                            | Sprint 4 backlog — `aria-invalid={Boolean(error)}` |
| 8.4 | P2       | D7 visual | Bulk-CSV modal (`BulkAttributeValuesModal`) — error rows обрабатываются inline ✓, но preview не показывает что попало в `validItems`                                                               | Sprint 4 backlog                                   |
| 8.5 | P3       | D8 Perf   | Trinity attribute lists без virtualization (cap=200/500)                                                                                                                                           | Long-term                                          |

## /admin/settings/attribute-templates — bindings DnD

| #   | Severity | Dimension | Issue                                                                                                                                                                                                                          | Fix                                                                 |
| --- | -------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| 9.1 | P1       | D5 a11y   | `BindingsList` items имеют `tabIndex={0}` ✓ + `aria-label="Список привязок"`. Но **нет `aria-live` announcer** при reorder — DnD/keyboard перенос row не объявляется screen reader (в `ImagesSection` это сделано, тут забыли) | Добавить aria-live polite announcer как в `ImagesSection`           |
| 9.2 | P1       | D5 a11y   | `BindingsList` drag handle `⋮⋮` (line 168) — symbol через `aria-hidden="true"` ✓ — ОК. Но `title="Перетащить (Alt+↑/↓ для клавиатуры)"` — title на `<span>` обычно screen reader не читает. Hint скрытен                       | Заменить span на `<button>` или добавить visually-hidden описание   |
| 9.3 | P1       | D5 a11y   | `AssignToCategoryModal` — fan-out PATCH без `aria-busy` на список во время mutation. Если пользователь чекнул 50 категорий и ждёт — список выглядит интерактивным                                                              | Add `aria-busy={mutation.isPending}` на `<ul>`                      |
| 9.4 | P2       | D7 visual | `CloneTemplateModal` сразу router.push на новый template detail — **без opportunity для пользователя отменить** или продолжить работу с оригинальным                                                                           | Sprint 4 backlog — добавить toast "Создан клон, открыть?" с кнопкой |
| 9.5 | P2       | D8 Perf   | `AssignToCategoryModal` `flattenTree` обрабатывает каждый rendered с `tree`. ОК для малого tree, но при росте ассортимента может нагружать                                                                                     | Sprint 4 backlog                                                    |
| 9.6 | P3       | D5 a11y   | `confirm()` (нативный браузерный) для unbind — недоступен в screen-reader-friendly виде                                                                                                                                        | Long-term — заменить на кастомный `<DeleteConfirmDialog>`           |

---

## Sprint 4 backlog (P2 / P3)

| Tag                   | Findings                                                                     |
| --------------------- | ---------------------------------------------------------------------------- |
| **a11y**              | 1.14, 1.15, 2.5, 2.6, 2.8, 2.11, 3.4, 3.7, 5.1, 5.2, 5.3, 7.5, 7.6, 8.3, 9.6 |
| **error-states**      | 1.8, 3.3, 4.4, 6.3                                                           |
| **empty-states**      | 1.9, 3.6, 5.4                                                                |
| **optimistic / live** | 1.10, 1.13, 9.4                                                              |
| **forms**             | 6.4, 8.4                                                                     |
| **performance**       | 1.12, 2.9, 3.5, 8.5, 9.5                                                     |
| **visual polish**     | 1.11, 3.8, 4.5, 6.5, 8.4                                                     |
| **i18n**              | (нет — все RU coverage чистое)                                               |

Группировать в Sprint 4 task-list — по тэгу. Базовые точки приложения:

- `entities/product`: optimistic updates, formatMoney в shared, live SSE indicator
- `features/product-form`: onBlur slug validation, focus return on error scroll, validation summary buttons
- `entities/category` + tree component: WAI-ARIA tree role
- `shared/ui/Modal`: focus return после finding 1.6 (P1, fix in this sprint)
- Auth slice: `?next=` параметр для redirect

## Methodology log

- 2026-05-10 — audit kicked off; doc skeleton created.
- 2026-05-10 — Phase A complete. 9 страниц × 9 dimensions, 65 findings (1 P0 / 26 P1 / 26 P2 / 12 P3). P2 / P3 уезжают в Sprint 4 backlog.
