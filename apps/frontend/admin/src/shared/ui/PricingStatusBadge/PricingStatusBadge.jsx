'use client';

import { cn } from '@/shared/lib/utils';

/**
 * Visual badge for the pricing FSM exposed by SKUResponse.
 *
 * The six states map 1:1 to the pricing recompute pipeline (ADR-005):
 *   - priced               — last recompute succeeded; sellingPrice valid
 *   - pending              — purchasePrice changed, recompute queued / running
 *   - stale_fx             — FX rate snapshot expired; selling price was last
 *                            valid value, will resync once a fresh rate lands
 *   - missing_purchase_price — purchasePrice unset; pipeline cannot compute
 *   - formula_error        — formula evaluation failed; see pricedFailureReason
 *   - legacy               — SKU pre-dates the recompute pipeline and has not
 *                            been re-saved; needs an explicit purchase or
 *                            manual price entry to enter the FSM
 *
 * `tooltip` is wired to the native `title` attribute. UI consumers should pass
 * `sku.pricedFailureReason` for error states; otherwise omit.
 */
export const PRICING_STATUSES = [
  'priced',
  'pending',
  'stale_fx',
  'missing_purchase_price',
  'formula_error',
  'legacy',
];

const STATUS_CONFIG = {
  priced: {
    label: 'Цена рассчитана',
    short: 'priced',
    dotClass: 'bg-app-success',
    bgClass: 'bg-emerald-50 text-emerald-700',
  },
  pending: {
    label: 'Считаем цену…',
    short: 'pending',
    // animate-pulse on the dot signals the recompute is live; helps users
    // distinguish "actually working" from "stuck on pending forever".
    dotClass: 'bg-amber-400 animate-pulse',
    bgClass: 'bg-amber-50 text-amber-700',
  },
  stale_fx: {
    label: 'Устаревший курс валют',
    short: 'stale fx',
    dotClass: 'bg-orange-400',
    bgClass: 'bg-orange-50 text-orange-700',
  },
  missing_purchase_price: {
    label: 'Нет закупочной цены',
    short: 'no cost',
    dotClass: 'bg-app-muted',
    bgClass: 'bg-app-card text-app-muted',
  },
  formula_error: {
    label: 'Ошибка формулы',
    short: 'error',
    dotClass: 'bg-app-danger',
    bgClass: 'bg-red-50 text-red-700',
  },
  legacy: {
    label: 'Legacy SKU — пересохраните цену',
    short: 'legacy',
    dotClass: 'bg-blue-400',
    bgClass: 'bg-blue-50 text-blue-700',
  },
};

export function PricingStatusBadge({
  status,
  tooltip,
  compact = false,
  className,
}) {
  const config = STATUS_CONFIG[status];

  // Unknown status from a future backend release shouldn't crash the table —
  // render a neutral placeholder badge so the row remains readable.
  if (!config) {
    return (
      <span
        className={cn(
          'bg-app-card text-app-muted inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-medium',
          className,
        )}
        title={tooltip ?? status}
      >
        <span className="bg-app-muted h-1.5 w-1.5 rounded-full" />
        {status}
      </span>
    );
  }

  return (
    <span
      role="status"
      aria-label={tooltip ? `${config.label}: ${tooltip}` : config.label}
      title={tooltip ?? config.label}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-medium',
        config.bgClass,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dotClass)} />
      {compact ? config.short : config.label}
    </span>
  );
}
