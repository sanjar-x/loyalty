'use client';

import { formatDateTime, cn, i18n } from '@/shared/lib/utils';
import { PricingStatusBadge } from '@/shared/ui/PricingStatusBadge/PricingStatusBadge';

// Display-side helpers — not exported because they're meaningful only for the
// "user-friendly money string" formatting required by this surface; cross-app
// money formatting belongs in @/shared/lib once a second consumer appears.
const CURRENCY_SYMBOLS = { RUB: '₽', CNY: '¥', USD: '$', EUR: '€' };

function formatMoney(money) {
  if (!money || money.amount == null) return '—';
  const userUnits = money.amount / 100;
  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(userUnits);
  const symbol = CURRENCY_SYMBOLS[money.currency] ?? money.currency;
  // RUB is post-positioned by Russian convention; CJK / Western symbols are
  // pre-positioned. Don't bother fighting Intl currency-display modes — the
  // visual difference users expect is too small to be worth the locale data.
  return money.currency === 'RUB'
    ? `${formatted} ${symbol}`
    : `${symbol} ${formatted}`;
}

// Best-effort human label for a variant-attribute pair. Admin endpoint
// doesn't denormalise nameI18N today (backend backlog), so we fall back
// down a friendliness ladder and finally truncate raw UUIDs into a short
// monospace tag — much easier to scan than a full 36-char UUID.
function shortenId(id) {
  if (typeof id !== 'string' || id.length <= 8) return id;
  return `${id.slice(0, 4)}…${id.slice(-4)}`;
}

function attrPairLabel(va) {
  const value =
    i18n(va.attributeValueNameI18N, '') ||
    va.attributeValueCode ||
    shortenId(va.attributeValueId) ||
    '';
  const attrName = i18n(va.attributeNameI18N, '') || va.attributeCode || null;
  // When we know the attribute name, render "Size: 42" so multiple
  // attributes don't collapse into an ambiguous slash list. Falls back to
  // a bare value when only the id is known.
  return attrName ? `${attrName}: ${value}` : value;
}

function attrSummary(sku) {
  const attrs = sku.variantAttributes ?? [];
  if (attrs.length === 0) return '—';
  return attrs.map(attrPairLabel).filter(Boolean).join(' · ');
}

/**
 * Read-only view of a product's SKU set with the CAT-003 pricing snapshot
 * surfaced (sellingPrice + status + lastUpdated).
 *
 * Designed to plug into the live SSE stream — `skus` is the *current* state
 * after `useSkuPricingEvents` has merged any push updates onto the original
 * server snapshot. The component itself is stateless.
 */
export function SkuPricingTable({ skus = [] }) {
  if (skus.length === 0) {
    return (
      <p className="text-app-muted bg-app-card rounded-xl px-4 py-6 text-center text-sm">
        Нет SKU для этого товара. Создайте варианты в форме редактирования.
      </p>
    );
  }

  return (
    <div className="border-app-border bg-app-panel overflow-hidden rounded-2xl border">
      <div
        role="row"
        className="border-app-border bg-app-card text-app-muted grid grid-cols-[minmax(140px,1.2fr)_minmax(140px,1.4fr)_repeat(3,minmax(110px,1fr))_140px_minmax(140px,180px)] items-center gap-3 border-b px-4 py-2 text-[11px] font-semibold tracking-wide uppercase"
      >
        <span>SKU</span>
        <span>Атрибуты</span>
        <span>Цена продажи</span>
        <span>Закупка</span>
        <span>Расчётная</span>
        <span>Статус</span>
        <span>Обновлено</span>
      </div>
      <ul className="divide-app-border divide-y">
        {skus.map((sku) => (
          <li
            key={sku.id ?? sku.skuCode}
            role="row"
            className="grid grid-cols-[minmax(140px,1.2fr)_minmax(140px,1.4fr)_repeat(3,minmax(110px,1fr))_140px_minmax(140px,180px)] items-center gap-3 px-4 py-2.5 text-sm"
          >
            <code className="text-app-text font-mono text-xs">
              {sku.skuCode}
            </code>
            <span className="text-app-text truncate">{attrSummary(sku)}</span>
            <span
              className={cn(
                'text-app-text',
                !sku.price && 'text-app-muted text-xs',
              )}
            >
              {formatMoney(sku.price)}
            </span>
            <span
              className={cn(
                'text-app-text',
                !sku.purchasePrice && 'text-app-muted text-xs',
              )}
            >
              {formatMoney(sku.purchasePrice)}
            </span>
            <span
              className={cn(
                'text-app-text font-medium',
                !sku.sellingPrice && 'text-app-muted text-xs font-normal',
              )}
            >
              {formatMoney(sku.sellingPrice)}
            </span>
            <PricingStatusBadge
              status={sku.pricingStatus ?? 'missing_purchase_price'}
              tooltip={sku.pricedFailureReason ?? undefined}
              compact
            />
            <span className="text-app-muted text-xs">
              {sku.pricedAt ? formatDateTime(sku.pricedAt) : '—'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
