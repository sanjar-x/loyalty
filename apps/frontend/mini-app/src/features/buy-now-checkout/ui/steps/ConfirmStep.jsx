'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

import { humanizeApiError, normalizeApiError } from '@/shared/api/errors';
import { toast } from '@/shared/ui/Toaster';
import { useAddCartItemMutation } from '@/entities/cart';

// Cross-feature import accepted: reuse cart-flow's shared rate-quote mapper
// (CHK-024 schema). Same rationale as PickupStep.
// eslint-disable-next-line no-restricted-imports
import { mapRateQuoteResponseToQuote } from '@/features/checkout-flow';

import {
  isBuyNowDisabledError,
  isPassportRequiredError,
  isQuoteExpiredError,
  useBuyNowOrderMutation,
  useBuyNowRateQuoteMutation,
} from '../../api/buyNowApi';
import {
  BuyNowStep,
  supplierTypeRequiresPassport,
  useBuyNowStore,
} from '../../model/useBuyNowCheckout';
import styles from '../BuyNowSheet.module.css';

/**
 * Step 4 — Review totals + pay.
 *
 * Pipeline on tap «Подтвердить»:
 *   1. validate (skuId / recipientId / pickup / quote / idempotency key)
 *   2. POST /api/v1/orders/buy-now with the persisted idempotency key
 *      (same key on retry — backend dedup scope `order.create_buy_now`,
 *      TTL 24h, see ADR-010)
 *   3. on `ORDER_DELIVERY_QUOTE_EXPIRED` (410) — silent refetch of the
 *      quote (one attempt) → retry POST. If the second attempt is also
 *      expired we surface a toast and leave the customer on this step.
 *   4. on `BUY_NOW_DISABLED` (503) — mark the store disabled (Sprint 1.5
 *      kill-switch) and render a cart-fallback UI; consumers also greys
 *      out the «Купить сейчас» PDP button via `useBuyNowStore.isDisabledNow()`.
 *   5. on 201 — `setSuccess` and branch on `autoCaptured`:
 *        • true  → router.push('/profile/orders/' + orderId) immediately
 *        • false → render the PSP-loader placeholder, then auto-redirect
 *                  after a short delay (FE-5 stub; Q4 — real PSP integration
 *                  is deferred indefinitely, branch is kept as a safety net)
 *   6. on any other error envelope — toast with `error.message` from the
 *      envelope + store ERROR state.
 *
 * ADR-010 references: I1 (no cart mutation here), I2 (`recipientId` is
 * required and resolved earlier), I3 (`autoCaptured=true` is the
 * skip-payment short-circuit ⇒ direct navigation), I4 (quote ownership /
 * currency checks happen server-side via `resolve_delivery_quote`).
 *
 * NOTE FE-6: Buy Now path MUST NOT write `localStorage.loyaltymarket_cart_meta_v1`
 * — that store is cart-display metadata only. The Buy Now flow does not
 * touch cart state by contract (ADR-010 I1).
 */

// Pretend-PSP redirect delay when `autoCaptured === false`. Real PSP
// integration is deferred (Q4); the loader gives the customer a brief
// affordance before we shuttle them to the order page.
const FAKE_PSP_REDIRECT_DELAY_MS = 1500;

export default function ConfirmStep({ onClose }) {
  const router = useRouter();

  const status = useBuyNowStore((s) => s.status);
  const skuId = useBuyNowStore((s) => s.skuId);
  const quantity = useBuyNowStore((s) => s.quantity);
  const recipientId = useBuyNowStore((s) => s.recipientId);
  const passportId = useBuyNowStore((s) => s.passportId);
  const pickup = useBuyNowStore((s) => s.pickup);
  const quote = useBuyNowStore((s) => s.quote);
  const idempotencyKey = useBuyNowStore((s) => s.idempotencyKey);
  const error = useBuyNowStore((s) => s.error);
  const orderId = useBuyNowStore((s) => s.orderId);
  const payment = useBuyNowStore((s) => s.payment);
  const productMeta = useBuyNowStore((s) => s.productMeta);
  const disabledReason = useBuyNowStore((s) => s.disabledReason);

  const beginSubmit = useBuyNowStore((s) => s.beginSubmit);
  const setSuccess = useBuyNowStore((s) => s.setSuccess);
  const setError = useBuyNowStore((s) => s.setError);
  const setQuote = useBuyNowStore((s) => s.setQuote);
  const reset = useBuyNowStore((s) => s.reset);
  const markDisabled = useBuyNowStore((s) => s.markDisabled);
  const goToStep = useBuyNowStore((s) => s.goToStep);

  const [buyNow, mutationState] = useBuyNowOrderMutation();
  const [refreshQuoteMutation, quoteState] = useBuyNowRateQuoteMutation();
  const [addCartItem, cartAddState] = useAddCartItemMutation();

  const inflightRef = useRef(false);
  const isBusy =
    status === BuyNowStep.SUBMITTING || mutationState.isLoading || quoteState.isLoading;

  const refreshQuoteOnce = useCallback(async () => {
    if (!skuId || !pickup?.providerCode || !pickup?.externalId) return null;
    try {
      const resp = await refreshQuoteMutation({
        items: [{ skuId, quantity }],
        providerCode: pickup.providerCode,
        pickupPointExternalId: pickup.externalId,
        serviceCode: quote?.serviceCode ?? null,
      }).unwrap();
      const mapped = mapRateQuoteResponseToQuote(resp);
      if (mapped) {
        setQuote(mapped);
        return mapped;
      }
      return null;
    } catch (err) {
      console.warn('[buy-now] quote refresh failed', err);
      return null;
    }
  }, [skuId, quantity, pickup, quote?.serviceCode, refreshQuoteMutation, setQuote]);

  const submitOrder = useCallback(
    async (deliveryQuoteId) =>
      buyNow({
        skuId,
        quantity,
        recipientId,
        // ADR-011: passportId is required at handler-level for
        // cross-border SKUs and ignored otherwise. We send it whenever
        // the store has resolved one — LOCAL flow leaves it null so the
        // backend's `Optional[passport_id]` schema accepts the payload.
        passportId: passportId ?? null,
        pickupCarrier: pickup.providerCode,
        pickupPointId: pickup.externalId,
        deliveryQuoteId,
        idempotencyKey,
        paymentProvider: 'fake',
      }).unwrap(),
    [buyNow, skuId, quantity, recipientId, passportId, pickup, idempotencyKey]
  );

  const handleConfirm = async () => {
    if (inflightRef.current) return;
    if (!skuId || !recipientId || !pickup?.externalId || !pickup?.providerCode) return;
    // Defence-in-depth: a cross-border SKU without a resolved passport
    // would land at the backend invariant I2 anyway, but we guard the
    // confirm tap so the customer goes straight back to PassportStep
    // instead of waiting for the round-trip.
    if (supplierTypeRequiresPassport(productMeta?.supplierType) && !passportId) {
      toast.error('Заполните паспорт получателя для cross-border заказа');
      goToStep(BuyNowStep.PASSPORT);
      return;
    }
    if (!quote?.quoteId) {
      toast.error('Сначала рассчитайте стоимость доставки');
      return;
    }
    if (!idempotencyKey) {
      // BuyNowSheet mints the key at CONFIRM-eligible states; this
      // guards against a race where the user mashes confirm before the
      // key effect runs.
      toast.error('Не удалось подготовить идемпотентность, попробуйте ещё раз');
      return;
    }
    inflightRef.current = true;
    beginSubmit();

    try {
      let resp;
      try {
        resp = await submitOrder(quote.quoteId);
      } catch (err) {
        if (isBuyNowDisabledError(err)) {
          markDisabled('BUY_NOW_DISABLED');
          setError({
            code: 'BUY_NOW_DISABLED',
            message: 'Buy Now временно недоступен',
          });
          return;
        }
        if (isPassportRequiredError(err)) {
          // ADR-011 I2: backend rejected the order because the SKU is
          // cross-border but no passport was attached. Usually this is
          // a Gap A regression (supplierType didn't reach the FSM) —
          // bounce the customer to PASSPORT so they can resolve one.
          toast.error('Для cross-border заказа нужен паспорт получателя');
          setError({
            code: 'PASSPORT_REQUIRED_FOR_CROSS_BORDER',
            message: 'Требуется паспорт',
          });
          goToStep(BuyNowStep.PASSPORT);
          return;
        }
        if (isQuoteExpiredError(err)) {
          const refreshed = await refreshQuoteOnce();
          if (!refreshed?.quoteId) {
            toast.error('Стоимость доставки изменилась, проверьте сумму');
            setError({
              code: 'ORDER_DELIVERY_QUOTE_EXPIRED',
              message: 'Срок котировки истёк',
            });
            return;
          }
          try {
            resp = await submitOrder(refreshed.quoteId);
          } catch (retryErr) {
            if (isBuyNowDisabledError(retryErr)) {
              markDisabled('BUY_NOW_DISABLED');
              setError({
                code: 'BUY_NOW_DISABLED',
                message: 'Buy Now временно недоступен',
              });
              return;
            }
            if (isPassportRequiredError(retryErr)) {
              toast.error('Для cross-border заказа нужен паспорт получателя');
              setError({
                code: 'PASSPORT_REQUIRED_FOR_CROSS_BORDER',
                message: 'Требуется паспорт',
              });
              goToStep(BuyNowStep.PASSPORT);
              return;
            }
            if (isQuoteExpiredError(retryErr)) {
              toast.error('Стоимость доставки изменилась, проверьте сумму');
              setError({
                code: 'ORDER_DELIVERY_QUOTE_EXPIRED',
                message: 'Срок котировки истёк (повторно)',
              });
              return;
            }
            const norm = normalizeApiError(retryErr);
            setError({ code: norm.code, message: norm.message });
            toast.error(humanizeApiError(retryErr, 'Не удалось оформить заказ'));
            return;
          }
        } else {
          const norm = normalizeApiError(err);
          setError({ code: norm.code, message: norm.message });
          toast.error(humanizeApiError(err, 'Не удалось оформить заказ'));
          return;
        }
      }

      setSuccess({
        orderId: resp.orderId,
        payment: {
          paymentIntentId: resp.paymentIntentId,
          clientSecret: resp.clientSecret ?? null,
          totalAmount: resp.totalAmount,
          currency: resp.currency,
          autoCaptured: Boolean(resp.autoCaptured),
        },
      });

      if (resp.autoCaptured) {
        reset();
        onClose?.();
        router.push(`/profile/orders/${encodeURIComponent(resp.orderId)}`);
      }
      // else: status stays SUCCESS — the PSP loader renders below and
      // auto-redirects after FAKE_PSP_REDIRECT_DELAY_MS.
    } finally {
      inflightRef.current = false;
    }
  };

  const handleSwitchToCart = useCallback(async () => {
    if (!skuId) return;
    try {
      await addCartItem({ skuId, quantity }).unwrap();
      reset();
      onClose?.();
      router.push('/cart');
    } catch (err) {
      toast.error(humanizeApiError(err, 'Не удалось добавить в корзину'));
    }
  }, [addCartItem, skuId, quantity, reset, onClose, router]);

  /* ── Render branches ── */

  // Kill-switch fallback (Sprint 1.5). Customer sees this on a fresh
  // attempt within the TTL window or right after a 503 mid-attempt.
  if (disabledReason === 'BUY_NOW_DISABLED') {
    return (
      <div className={styles.stepRoot}>
        <div className={styles.stepTitle}>Купить сейчас временно недоступен</div>
        <div className={styles.stepHint}>
          Сервис покупки в один шаг сейчас отключён. Воспользуйтесь обычной корзиной — мы добавим
          товар туда.
        </div>
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={handleSwitchToCart}
          disabled={cartAddState.isLoading}
        >
          {cartAddState.isLoading ? 'Добавляем…' : 'Перейти в корзину'}
        </button>
      </div>
    );
  }

  if (status === BuyNowStep.SUCCESS && payment && !payment.autoCaptured) {
    return <PspLoader orderId={orderId} onRedirect={onClose} />;
  }

  return (
    <div className={styles.stepRoot}>
      <div className={styles.stepTitle}>4. Подтверждение</div>

      <Summary
        productMeta={productMeta}
        skuId={skuId}
        quantity={quantity}
        recipientId={recipientId}
        pickup={pickup}
        quote={quote}
      />

      {error ? (
        <div className={styles.placeholder} role="alert">
          {error.message || error.code || 'Не удалось оформить заказ'}
        </div>
      ) : null}

      <button
        type="button"
        className={styles.primaryBtn}
        onClick={handleConfirm}
        disabled={!quote?.quoteId || isBusy}
        aria-busy={isBusy}
      >
        {isBusy ? 'Оформляем…' : 'Подтвердить и оплатить'}
      </button>
    </div>
  );
}

/* ─────────────────────────────  Summary  ────────────────────────────── */

function Summary({ productMeta, skuId, quantity, recipientId, pickup, quote }) {
  const itemPriceKopecks =
    typeof productMeta?.priceKopecks === 'number'
      ? productMeta.priceKopecks
      : typeof productMeta?.priceRub === 'number'
        ? Math.round(productMeta.priceRub * 100)
        : null;
  const itemsTotalKopecks =
    itemPriceKopecks != null ? itemPriceKopecks * Math.max(1, quantity) : null;
  const deliveryKopecks = quote?.deliveryAmount ?? 0;
  const totalKopecks = itemsTotalKopecks != null ? itemsTotalKopecks + deliveryKopecks : null;

  return (
    <div className={styles.stepHint}>
      <div>
        <strong>{productMeta?.name || 'Товар'}</strong>
        {productMeta?.variantLabel ? ` · ${productMeta.variantLabel}` : ''} · ×{quantity}
      </div>
      <div>
        Получатель:{' '}
        {recipientId ? <span style={{ color: '#0a8a3a' }}>✓ выбран</span> : <span>—</span>}
      </div>
      <div>
        ПВЗ:{' '}
        {pickup?.externalId
          ? `${pickup.providerCode?.toUpperCase()} · ${pickup.address || pickup.externalId}`
          : '—'}
      </div>
      {itemsTotalKopecks != null ? (
        <div>Товары: {Math.floor(itemsTotalKopecks / 100)} ₽</div>
      ) : null}
      <div>Доставка: {Math.floor(deliveryKopecks / 100)} ₽</div>
      {totalKopecks != null ? (
        <div style={{ fontWeight: 600, color: '#111' }}>
          Итого: {Math.floor(totalKopecks / 100)} ₽
        </div>
      ) : null}
      {!skuId ? <div style={{ color: '#c33' }}>SKU отсутствует — переоткройте sheet</div> : null}
    </div>
  );
}

/* ─────────────────────────────  PSP stub  ───────────────────────────── */

/**
 * FE-5 placeholder shown when backend returns `autoCaptured: false`.
 * Per product Q4, real PSP integration is deferred indefinitely — the
 * production deployment runs with `PAYMENT_AUTO_CAPTURE_ON_AUTHORIZE=true`
 * so this branch is currently unreachable. Kept as a safety net so the
 * customer is not stranded if the server ever flips the flag without a
 * matching frontend release.
 */
function PspLoader({ orderId, onRedirect }) {
  const router = useRouter();
  const reset = useBuyNowStore((s) => s.reset);

  useEffect(() => {
    if (!orderId) return;
    const timer = setTimeout(() => {
      reset();
      onRedirect?.();
      router.push(`/profile/orders/${encodeURIComponent(orderId)}`);
    }, FAKE_PSP_REDIRECT_DELAY_MS);
    return () => clearTimeout(timer);
  }, [orderId, onRedirect, reset, router]);

  return (
    <div className={styles.stepRoot} role="status" aria-live="polite">
      <div className={styles.stepTitle}>Заказ создан</div>
      <div className={styles.stepHint}>
        Обрабатываем оплату, перенаправим к заказу через мгновение…
      </div>
      <div className={styles.placeholder}>
        <span style={{ fontFamily: 'monospace', fontSize: 11 }}>orderId: {orderId}</span>
      </div>
    </div>
  );
}
