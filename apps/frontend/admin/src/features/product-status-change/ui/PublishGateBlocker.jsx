'use client';

import { PRICING_NEXT_STEP_HINTS } from '@/entities/product';
import { PricingStatusBadge } from '@/shared/ui/PricingStatusBadge/PricingStatusBadge';
import { cn } from '@/shared/lib/utils';

/**
 * Per-SKU breakdown shown when backend returns PRODUCT_NOT_READY (CAT-019).
 *
 * Renders a row for every entry in `diagnostics`, with:
 *   - SKU code + pricing status badge
 *   - Backend-provided `nextStep` hint (falls back to local table if absent)
 *   - Action button(s):
 *       • "Закупочная цена" — opens the bulk price modal pre-highlighting this SKU
 *       • "Повторить" — for `pending` rows, re-runs the publish mutation
 *
 * The component is presentational — orchestration (mutation retry, opening
 * the bulk modal) is owned by the parent page so the blocker stays decoupled
 * from feature-layer hooks.
 */
export function PublishGateBlocker({
  diagnostics = [],
  onSetPurchasePrice,
  onRetry,
  retrying = false,
}) {
  if (diagnostics.length === 0) return null;

  return (
    <section
      role="alert"
      aria-labelledby="publish-gate-blocker-title"
      className="border-app-danger rounded-xl border bg-red-50/40 p-4"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3
            id="publish-gate-blocker-title"
            className="text-app-danger text-sm font-semibold"
          >
            Не все SKU готовы к публикации
          </h3>
          <p className="text-app-muted mt-1 text-xs">
            Backend заблокировал публикацию — устраните указанное ниже и
            повторите.
          </p>
        </div>
      </div>

      <div className="border-app-border bg-app-panel overflow-hidden rounded-lg border">
        <table className="min-w-full text-sm">
          <thead className="bg-app-card text-app-muted text-[11px] font-semibold tracking-wide uppercase">
            <tr>
              <th className="px-3 py-2 text-left">SKU</th>
              <th className="px-3 py-2 text-left">Статус</th>
              <th className="px-3 py-2 text-left">Что делать</th>
              <th className="px-3 py-2 text-right">Действие</th>
            </tr>
          </thead>
          <tbody className="divide-app-border divide-y">
            {diagnostics.map((d) => {
              const fallbackStep =
                PRICING_NEXT_STEP_HINTS[d.pricingStatus] ??
                'Откройте SKU для уточнения';
              const stepText = d.nextStep || fallbackStep;
              const isPending = d.pricingStatus === 'pending';
              // Pending rows already have a purchase price — recompute is in
              // flight, the action they need is "wait + retry", not edit cost.
              const canEditPurchase =
                !isPending &&
                (!d.hasPurchasePrice ||
                  d.pricingStatus === 'missing_purchase_price' ||
                  d.pricingStatus === 'legacy' ||
                  d.pricingStatus === 'formula_error' ||
                  d.pricingStatus === 'stale_fx');

              return (
                <tr key={d.skuId} className="align-top">
                  <td className="text-app-text px-3 py-2 font-mono text-xs">
                    {d.skuCode || d.skuId.slice(0, 8)}
                  </td>
                  <td className="px-3 py-2">
                    <PricingStatusBadge
                      status={d.pricingStatus}
                      tooltip={d.failureReason ?? undefined}
                      compact
                    />
                  </td>
                  <td className="text-app-text px-3 py-2 text-xs">
                    {stepText}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="inline-flex flex-wrap justify-end gap-2">
                      {isPending && (
                        <button
                          type="button"
                          onClick={onRetry}
                          disabled={retrying}
                          className={cn(
                            'border-app-border text-app-text rounded-md border bg-white px-2.5 py-1 text-xs font-medium',
                            'hover:bg-app-card disabled:opacity-50',
                          )}
                        >
                          {retrying ? 'Повтор...' : 'Повторить'}
                        </button>
                      )}
                      {canEditPurchase && (
                        <button
                          type="button"
                          onClick={() => onSetPurchasePrice?.(d.skuId)}
                          className="bg-app-text-dark rounded-md px-2.5 py-1 text-xs font-medium text-white hover:opacity-90"
                        >
                          Закупочная цена
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
