/**
 * Pure pricing-FSM helpers shared between the product detail page (publish
 * gate) and the form (publishable check). Lives at the `entities/product`
 * layer — no UI, no React, no features-layer imports — so both consumers can
 * pull from one source of truth without crossing FSD boundaries.
 *
 * Mirrors backend rules:
 *   - publish accepts either manual `sku.price` or autonomous
 *     `sku.sellingPrice` (= `pricingStatus === 'priced'`)
 *   - `pending` / `formula_error` / `stale_fx` / `missing_purchase_price`
 *     are explicitly NOT publishable
 *   - `legacy` SKUs predate the recompute pipeline; they need a fresh
 *     purchase or manual price write to enter the FSM
 */

/**
 * Pricing FSM states that block publish. Single list — when backend adds a
 * new failure status, only this constant needs editing.
 */
export const PRICING_FAILURE_STATUSES = [
  'formula_error',
  'stale_fx',
  'missing_purchase_price',
];

const PRICING_FAILURE_LABELS = {
  formula_error: 'Ошибка формулы',
  stale_fx: 'Устаревший курс валют',
  missing_purchase_price: 'Не задана закупочная цена',
};

// Backend-reported next-step hints for each pricing FSM state. Surfaced in
// PublishGateBlocker rows alongside the SKU-specific `nextStep` from the
// CAT-019 diagnostics envelope — used as a fallback when the backend
// payload is missing (older response, network truncation).
export const PRICING_NEXT_STEP_HINTS = {
  pending: 'Дождитесь расчёта (~5 сек) и повторите публикацию',
  missing_purchase_price: 'Введите закупочную цену для этого SKU',
  stale_fx: 'Обновите курс валют в Pricing → Contexts',
  formula_error: 'Проверьте формулу или задайте цену продажи вручную',
  legacy: 'Пересохраните закупочную цену или задайте цену продажи',
  priced: 'Эта SKU уже готова — обновите страницу',
};

/**
 * Per-SKU publish-readiness check.
 *
 * A SKU is publishable when it has either a manual price or an autonomous
 * pricing result that has actually landed. Anything still pending, in a
 * failure state, or in the legacy bucket keeps publish gated.
 */
export function skuPublishable(sku) {
  if (!sku) return false;
  if (sku.price?.amount != null && Number(sku.price.amount) > 0) return true;
  if (
    sku.purchasePrice?.amount != null &&
    Number(sku.purchasePrice.amount) > 0
  ) {
    return sku.pricingStatus === 'priced';
  }
  return false;
}

/**
 * Aggregate publish gate for a product's SKU set.
 *
 * Returns `{ blocked: boolean, reason: string | null }` matching the shape
 * <StatusTransitionBar publishGate=…> expects.
 *
 * Block order (most-specific first):
 *   1. any SKU in a failure state — surface the reason on the bar
 *   2. legacy SKUs (predate recompute pipeline) — block until re-saved
 *   3. autonomous-pricing SKUs still waiting on recompute
 *   4. nothing entered anywhere — say so client-side rather than wait for
 *      backend `PRODUCT_NOT_READY`
 */
export function computePublishGate(skus) {
  if (!skus.length) return { blocked: false, reason: null };
  const failure = skus.find((s) =>
    PRICING_FAILURE_STATUSES.includes(s.pricingStatus),
  );
  if (failure) {
    const label =
      PRICING_FAILURE_LABELS[failure.pricingStatus] ?? failure.pricingStatus;
    const reason = failure.pricedFailureReason
      ? `${label}: ${failure.pricedFailureReason}`
      : label;
    return { blocked: true, reason };
  }
  const legacy = skus.find(
    (s) => s.pricingStatus === 'legacy' && !skuPublishable(s),
  );
  if (legacy) {
    return {
      blocked: true,
      reason:
        'Часть SKU не прошла пересчёт цен — пересохраните закупочную цену.',
    };
  }
  const blockingPending = skus.some(
    (s) => !skuPublishable(s) && s.purchasePrice && !s.price,
  );
  if (blockingPending) {
    return {
      blocked: true,
      reason: 'Цены пересчитываются. Обычно занимает ~1 минуту.',
    };
  }
  const noPricingAnywhere = skus.every((s) => !s.price && !s.purchasePrice);
  if (noPricingAnywhere) {
    return {
      blocked: true,
      reason:
        'Не задана цена ни одной SKU — добавьте цену продажи или закупки.',
    };
  }
  return { blocked: false, reason: null };
}
