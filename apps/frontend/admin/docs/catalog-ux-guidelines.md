# Catalog UX guidelines

Reference for contributors touching catalog admin surfaces (products,
categories, brands, attributes, attribute templates). Patterns are
distilled from the audit landed in `docs/catalog-ux-audit-2026-05-10.md`
and the Phase B atomic fixes that resolved every P0/P1 finding.

When you ship a new admin page or component, walk through this list
before opening the PR. If you deviate from a guideline, leave a note
in the PR explaining why so the next reviewer doesn't try to "fix" it.

## 1 · Loading & layout shift

- **Initial load → render a layout-matching skeleton, never just
  «Загрузка…».** Use `<ProductDetailSkeleton>` / `<ProductEditSkeleton>`
  as references, or compose new skeletons from
  `<Skeleton>` / `<Skeleton.Bar>` / `<Skeleton.Block>` /
  `<Skeleton.Circle>` in `@/shared/ui/Skeleton`. The skeleton should
  occupy the same vertical rhythm as the live content so the post-load
  swap doesn't shift layout.
- Wrap each page-level skeleton in
  `role="status" aria-live="polite" aria-label="Загружаем …"` — SR
  users hear one localized announcement, not a stream of pulses.

## 2 · Error surfaces

- **Every full-page failure goes through `<ApiErrorState>`**
  (`@/shared/ui/ApiErrorState`). It discriminates 403/404/5xx/other,
  surfaces `error.details.request_id` in monospace, and chooses
  retry vs home-link affordance per status. Never re-implement an
  ad-hoc «Не удалось загрузить» line.
- **Error blocks inside a form / modal use `role="alert"`** so SR
  users get the assertive announcement when the backend rejects a
  submit. Static info blocks (e.g. «атрибут используется»
  pre-submit advisory) use `role="status"` instead — never share
  the assertive channel with the actual error.
- **Surface the request_id** wherever the user might need to quote
  it to support. Format: `request_id: <id>` in muted monospace.
- **Submit-error copy lives in one helper.** Pattern:
  `formatSubmitError(err) → { short, long, isCancellation }`
  consumed by both the toast and the inline card. Don't ladder the
  same `code === '…'` mapping twice.

## 3 · Optimistic UI

For destructive list mutations (delete, archive, bulk delete):

```js
mutation: {
  onMutate: async (id) => {
    await queryClient.cancelQueries({ queryKey: keys.lists() });
    const snapshots = queryClient.getQueriesData({ queryKey: keys.lists() });
    for (const [key, data] of snapshots) {
      if (!data?.items) continue;
      queryClient.setQueryData(key, {
        ...data,
        items: data.items.filter((p) => p.id !== id),
        total: data.total != null ? Math.max(0, data.total - 1) : data.total,
      });
    }
    return { snapshots };
  },
  onError: (err, _id, ctx) => {
    for (const [key, data] of ctx?.snapshots ?? []) {
      queryClient.setQueryData(key, data);
    }
    setStatusError(err.message);
  },
  onSettled: () => invalidateLists(),
}
```

- Every cached list query for the entity must be patched in `onMutate`.
- `onError` rolls all snapshots back atomically — no half-updated UI.
- `onSettled` revalidates so optimistic drift (e.g. concurrent inserts
  changing `total`) reconciles with the server.

## 4 · Concurrency / ETag

The shared `client-fetch` interceptor catches `412` and rethrows
`{code: 'OPTIMISTIC_LOCK_FAILED'}`. Any feature mutation that PATCHes
a versioned resource must:

1. Use the helper `isConcurrencyConflict(err)` from
   `@/features/product-form/model/useUpdateProduct` (or import the
   pattern). It accepts `status === 409 || 412 || code === 'OPTIMISTIC_LOCK_FAILED'`
   and a legacy substring match.
2. Show the localized message
   `«Товар был изменён другим пользователем. Обновите страницу и
попробуйте снова.»` instead of the raw status string.
3. Leave the form in its current state — never auto-refresh, the
   user would lose unsubmitted edits.

## 5 · Modal accessibility

`<Modal>` (`@/shared/ui/Modal`) provides:

- Focus trap that cycles forward/backward via Tab/Shift+Tab, locked
  to the visible focusables inside the dialog.
- First-focusable autofocus one frame after open.
- Esc / outside click → onClose (already wired).
- Focus restoration to the trigger on close.

When a modal renders a busy section (e.g. fan-out PATCH on
AssignToCategoryModal), set `aria-busy={mutation.isPending}` on the
list/region — AT marks it as «работает» instead of leaving the user
to discover that every checkbox is disabled.

## 6 · Form fields & ARIA

- `aria-invalid={Boolean(error) || undefined}` whenever the input has
  inline validation.
- `aria-describedby` always points at a static help id, plus a
  conditionally-rendered error id. Browsers ignore non-rendered refs
  so it's safe to list both. Help text is muted, error text is
  `text-app-danger` and ships `role="alert"` so the announcement
  fires when the validation flips invalid.
- For status-cycle text (e.g. upload progress flipping
  «Загрузка → Обработка → Готово») wrap the paragraph in
  `aria-live="polite" aria-atomic="true"` — SR users hear each
  transition without interrupting current speech.

## 7 · Disabled vs inert

- `disabled` on the actual `<input>` / `<button>` / `<select>` is the
  primary signal. Combine with `aria-disabled` on a parent only if
  you need the wrapper to be announced.
- For "this whole sub-region is non-interactive on this view" (e.g.
  variant-2 form locks variant-1 fields), prefer the HTML `inert`
  attribute on the wrapper. It removes the entire subtree from the
  tab order AND the click pipeline in one shot — no `pointer-events`
  hack that leaves keyboard focus orphaned. Pair with a visible
  «Наследуется» / «Заблокировано» badge OUTSIDE the inert region so
  SR users still hear the explanation.

## 8 · Decorative glyphs & icons

Every emoji or unicode glyph used as visual shorthand goes inside a
host with `aria-hidden="true"` so SR users hear only the textual
label. Examples:

```jsx
<button aria-label="Зафиксировать slug">
  <span aria-hidden="true">{slugEditing ? '✓' : '✎'}</span>
</button>

<li>
  <span aria-hidden="true">📚</span> справочник
</li>
```

If the glyph IS the only label (like a status indicator with no
text), give the host an `aria-label` instead.

## 9 · Reorderable lists

When you build a DnD list with a keyboard fallback (Alt+↑ / Alt+↓):

- Add a single visually-hidden instructions paragraph at the top of
  the list and link it via `aria-describedby` on the `<ul>`. SR
  users hear the keyboard recipe; the visible drag handle stays
  decorative (`title` on a span is unreliable).
- Add a `role="status" aria-live="polite"` sr-only announcer that
  fires on every reorder with copy like
  `«<Имя>» перемещён на позицию N из M`. Pattern lives in
  `BindingsList.jsx` and `ImagesSection`.

## 10 · Status FSM colour map

Product status badges map to the shared `PRODUCT_STATUS_TONES`
constant in `@/entities/product` (WCAG-AA hex pairs). Don't
hand-pick Tailwind shades per usage — every badge for the same
status across the admin must match.

```js
const tone = PRODUCT_STATUS_TONES[product.status];
return tone ? { background: tone.bg, color: tone.fg } : undefined;
```

## 11 · Tree / hierarchical actions

`CategoryNode` is the canonical pattern:

- Hidden-on-rest action buttons reveal on `:focus-within`, not just
  hover, so keyboard-only users see the affordance the moment they
  Tab into the row.
- Expand/collapse glyph button carries `aria-expanded` mirroring the
  current state, plus `aria-label="Развернуть категорию X"` /
  `"Свернуть категорию X"` so SR users hear what changed.
- Action buttons (`+` / `✎`) carry `aria-label`, never just `title`.

## 12 · Severity rubric (when classifying findings)

| Tier | Meaning                                                                         |
| ---- | ------------------------------------------------------------------------------- |
| P0   | Blocks a user (data loss risk, completely-broken control, broken keyboard nav). |
| P1   | Real friction or AT regression that we can fix in this sprint.                  |
| P2   | Nice-to-have polish; defer to next sprint backlog.                              |
| P3   | Long-term — usually requires a bigger refactor or library swap.                 |

When you raise a UX bug, tag it with one of these so triage knows
whether to ship-block or backlog. Use the audit doc as the canonical
example of the format.

## Related

- `docs/catalog-ux-audit-2026-05-10.md` — the audit that drove these
  guidelines.
- `docs/ARCHITECTURE.md` — FSD layer boundaries (UI patterns are
  scoped to layers).
- `docs/product-creation-flow.md` — multi-step orchestration that
  illustrates several of the patterns above.
