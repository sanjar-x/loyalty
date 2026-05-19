/**
 * Buy-now RTKQ wrappers.
 *
 * Thin adapters over the codegen mutations
 * `useBuyNowOrderApiV1OrdersBuyNowPostMutation` and
 * `useQuoteForPickupPointApiV1StorefrontLogisticsRatesQuotePostMutation`.
 * Reasons we don't call the codegen hooks directly:
 *  1. Codegen takes wrapper-arg envelopes (`{ buyNowOrderRequest }` /
 *     `{ rateQuoteRequest }`); the wrappers flatten to plain payloads so
 *     call-sites don't repeat the envelope each time.
 *  2. Lets us layer extra metadata (analytics tags, retry policy,
 *     idempotency replay) in one place.
 *  3. Provides pure predicates (`isBuyNowDisabledError`,
 *     `isQuoteExpiredError`) so consumers can react to envelope codes
 *     without re-implementing the match.
 *
 * Wire-format reference: apps/backend/docs/buy-now-audit-2026-05.md
 * appendix B (camelCase, Spec §1). Error envelope reference: appendix C
 * + Sprint 1.5 addendum (`BUY_NOW_DISABLED` 503).
 *
 * ADR: apps/backend/docs/ADR-010-buy-now-standalone-endpoint.md
 *      (I1 cart isolation, I2 inline recipient).
 */
import {
  useBuyNowOrderApiV1OrdersBuyNowPostMutation,
  useQuoteForPickupPointApiV1StorefrontLogisticsRatesQuotePostMutation,
} from '@/shared/api/codegen/api';
import { normalizeApiError } from '@/shared/api/errors';

/**
 * Sprint 1.5 backend kill-switch (`BUY_NOW_ENABLED=false`). Returned as
 * HTTP 503 with the standard error envelope; we MUST distinguish it from
 * a transient `SERVICE_UNAVAILABLE` outage to avoid spamming retries when
 * Buy Now is intentionally off. Match on `error.code` rather than status
 * alone — backend reserves the right to bump the envelope status (e.g.
 * 423 Locked) later.
 *
 * @param {unknown} rtkError — RTKQ error (status + data envelope)
 * @returns {boolean}
 */
export function isBuyNowDisabledError(rtkError) {
  const { code } = normalizeApiError(rtkError);
  return code === 'BUY_NOW_DISABLED';
}

/**
 * Quote-expiry envelope from `_delivery.py::resolve_delivery_quote`.
 * Surfaced when the 30-min TTL elapses between PickupStep's quote fetch
 * and the actual POST /orders/buy-now. ConfirmStep refetches the quote
 * once and retries; if the second attempt also expires we surface a
 * user-visible "цена изменилась" toast.
 */
export function isQuoteExpiredError(rtkError) {
  const { code } = normalizeApiError(rtkError);
  return code === 'ORDER_DELIVERY_QUOTE_EXPIRED';
}

/**
 * ADR-011 backend invariant I2: cross-border SKUs require a passport.
 * If the FSM somehow advances past PASSPORT without resolving one
 * (e.g. a Gap A regression where `supplierType` didn't reach the
 * store and the step was skipped), the order POST fails with
 * `422 PASSPORT_REQUIRED_FOR_CROSS_BORDER`. ConfirmStep surfaces a
 * toast and bounces the customer to PASSPORT.
 */
export function isPassportRequiredError(rtkError) {
  const { code } = normalizeApiError(rtkError);
  return code === 'PASSPORT_REQUIRED_FOR_CROSS_BORDER';
}

export function useBuyNowOrderMutation() {
  const [trigger, state] = useBuyNowOrderApiV1OrdersBuyNowPostMutation();

  const wrapped = (payload) =>
    trigger({
      buyNowOrderRequest: {
        skuId: String(payload?.skuId ?? ''),
        quantity: Math.max(1, Math.min(99, Math.floor(Number(payload?.quantity) || 1))),
        recipientId: String(payload?.recipientId ?? ''),
        pickupCarrier: String(payload?.pickupCarrier ?? ''),
        pickupPointId: String(payload?.pickupPointId ?? ''),
        deliveryQuoteId: payload?.deliveryQuoteId ?? null,
        idempotencyKey: String(payload?.idempotencyKey ?? ''),
        paymentProvider: payload?.paymentProvider || 'fake',
      },
    });

  return [wrapped, state];
}

/**
 * /storefront/logistics/rates/quote wrapper for buy-now. Identical shape
 * to cart-flow's `useGetRateQuoteMutation` (features/checkout-flow/api/hooks.js)
 * but kept in this slice to avoid a cross-feature import. The two ride
 * the same backend handler (`storefront_logistics.router`), so behaviour
 * mirrors cart-flow exactly.
 *
 * Input — { items: [{skuId, quantity}], providerCode, pickupPointExternalId,
 *           serviceCode? }
 * Output — `RateQuoteResponse` (codegen schema): { quoteId, providerCode,
 *           serviceCode, serviceName, deliveryType, deliveryAmount: Money,
 *           currency, deliveryDaysMin, deliveryDaysMax, expiresAt,
 *           fallbackAlternatives[] }
 */
export function useBuyNowRateQuoteMutation() {
  const [trigger, state] = useQuoteForPickupPointApiV1StorefrontLogisticsRatesQuotePostMutation();

  const wrapped = ({ items, providerCode, pickupPointExternalId, serviceCode } = {}) =>
    trigger({
      rateQuoteRequest: {
        items: Array.isArray(items)
          ? items.map((it) => ({
              skuId: String(it?.skuId ?? ''),
              quantity: Math.max(1, Math.min(99, Math.floor(Number(it?.quantity) || 1))),
            }))
          : [],
        providerCode: String(providerCode ?? ''),
        pickupPointExternalId: String(pickupPointExternalId ?? ''),
        serviceCode: serviceCode ?? null,
      },
    });

  return [wrapped, state];
}
