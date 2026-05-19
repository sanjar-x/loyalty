'use client';

import { useEffect, useRef, useState } from 'react';

import { bulkUpdatePurchasePrice } from '@/entities/product';
import { Modal } from '@/shared/ui/Modal';
import { MoneyInput } from '@/shared/ui/MoneyInput/MoneyInput';
import { cn } from '@/shared/lib/utils';

const PURCHASE_CURRENCIES = ['RUB', 'CNY'];

function attrSummary(sku) {
  const attrs = sku.variantAttributes ?? [];
  if (attrs.length === 0) return '';
  return attrs
    .map(
      (va) =>
        va.attributeValueNameI18N?.ru ??
        va.attributeValueCode ??
        va.attributeValueId ??
        '',
    )
    .filter(Boolean)
    .join(' / ');
}

function prefillFromSku(sku) {
  const pp = sku.purchasePrice;
  if (!pp || pp.amount == null) return null;
  return { amount: Math.round(pp.amount / 100), currency: pp.currency };
}

/**
 * Bulk-edit purchasePrice for every SKU of a product (CAT-003).
 *
 * Backend takes the patch in one round-trip and returns a per-row envelope —
 * the modal renders both a global submit error (network/auth/service) and
 * per-row errors so the user can fix the broken rows without losing the
 * successful ones.
 */
export function BulkPurchasePriceModal({
  open,
  onClose,
  productId,
  skus = [],
  onApplied,
  highlightSkuId = null,
}) {
  // edits[skuId] = money | null. Reset to the SKU's current purchasePrice when
  // the modal opens so the user starts from the existing values rather than
  // an empty form.
  const [edits, setEdits] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  // perRow[skuId] = { ok: boolean, error?: { code?, message? } }
  const [perRow, setPerRow] = useState({});
  const [summary, setSummary] = useState(null);
  // Refs for highlight-target rows so we can scroll + focus when the modal
  // is opened from PublishGateBlocker (CAT-020).
  const rowRefs = useRef(new Map());

  useEffect(() => {
    if (!open) return;
    const next = {};
    for (const sku of skus) next[sku.id] = prefillFromSku(sku);
    setEdits(next);
    setSubmitError(null);
    setPerRow({});
    setSummary(null);
  }, [open, skus]);

  useEffect(() => {
    if (!open || !highlightSkuId) return;
    // Defer one frame so the modal portal is fully laid out before we scroll.
    const id = requestAnimationFrame(() => {
      const node = rowRefs.current.get(highlightSkuId);
      if (!node) return;
      node.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const input = node.querySelector('input');
      input?.focus();
    });
    return () => cancelAnimationFrame(id);
  }, [open, highlightSkuId]);

  function setRow(skuId, money) {
    setEdits((prev) => ({ ...prev, [skuId]: money }));
  }

  async function handleSubmit() {
    // Build the items array — only include rows where the user actually
    // entered a value. Sending null for untouched rows would clear them on
    // the backend, which is not what the UX implies.
    const items = Object.entries(edits)
      .filter(
        ([, money]) => money && money.amount != null && money.amount !== '',
      )
      .map(([skuId, money]) => ({
        skuId,
        purchasePrice: {
          amount: parseInt(money.amount, 10) * 100,
          currency: money.currency ?? 'RUB',
        },
      }));

    if (items.length === 0) {
      setSubmitError(
        'Укажите закупочную цену хотя бы для одного SKU прежде чем применять.',
      );
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    setPerRow({});
    setSummary(null);
    try {
      const res = await bulkUpdatePurchasePrice(productId, items);
      const rowMap = {};
      for (const r of res?.results ?? []) {
        rowMap[r.skuId] = r;
      }
      setPerRow(rowMap);
      const succeeded =
        res?.succeeded ?? (res?.results ?? []).filter((r) => r.ok).length;
      const failed =
        res?.failed ?? (res?.results ?? []).filter((r) => !r.ok).length;
      setSummary({ succeeded, failed });
      onApplied?.(res);
    } catch (err) {
      setSubmitError(err?.message ?? 'Не удалось применить закупочные цены');
    } finally {
      setSubmitting(false);
    }
  }

  function rowError(skuId) {
    const result = perRow[skuId];
    if (!result || result.ok) return null;
    return result.error?.message ?? 'Ошибка';
  }

  return (
    <Modal open={open} onClose={onClose} title="Закупочные цены — массово">
      <div className="flex flex-col gap-3">
        {summary && (
          <div
            role="status"
            className={cn(
              'rounded-lg px-3 py-2 text-xs',
              summary.failed > 0
                ? 'bg-amber-50 text-amber-700'
                : 'bg-emerald-50 text-emerald-700',
            )}
          >
            Успешно: <strong>{summary.succeeded}</strong>
            {summary.failed > 0 && (
              <>
                , с ошибками: <strong>{summary.failed}</strong>
              </>
            )}
          </div>
        )}

        {submitError && (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600"
          >
            {submitError}
          </div>
        )}

        {skus.length === 0 ? (
          <p className="text-app-muted text-sm">Нет SKU для редактирования.</p>
        ) : (
          <ul className="divide-app-border border-app-border max-h-[60vh] divide-y overflow-y-auto rounded-xl border">
            {skus.map((sku) => {
              const err = rowError(sku.id);
              const isHighlighted = sku.id === highlightSkuId;
              return (
                <li
                  key={sku.id}
                  ref={(node) => {
                    if (node) rowRefs.current.set(sku.id, node);
                    else rowRefs.current.delete(sku.id);
                  }}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 transition-colors',
                    err && 'bg-red-50/40',
                    isHighlighted &&
                      !err &&
                      'bg-amber-50 ring-2 ring-amber-200',
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <code className="text-app-text block font-mono text-xs">
                      {sku.skuCode}
                    </code>
                    <span className="text-app-muted block truncate text-[11px]">
                      {attrSummary(sku) || '—'}
                    </span>
                  </div>
                  <div className="w-44 shrink-0">
                    <MoneyInput
                      ariaLabel={`Закупочная цена ${sku.skuCode}`}
                      placeholder="0"
                      currencies={PURCHASE_CURRENCIES}
                      value={edits[sku.id] ?? null}
                      onChange={(money) => setRow(sku.id, money)}
                      hasError={Boolean(err)}
                      errorText={err ?? undefined}
                      disabled={submitting}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        <div className="mt-2 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="text-app-text hover:bg-app-card rounded-lg px-3 py-2 text-sm"
          >
            Закрыть
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || skus.length === 0}
            className={cn(
              'bg-app-text-dark rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity',
              submitting && 'opacity-60',
            )}
          >
            {submitting ? 'Применение…' : 'Применить'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
