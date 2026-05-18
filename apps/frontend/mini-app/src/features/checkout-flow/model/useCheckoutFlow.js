'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';

import {
  useGetMyCartQuery,
  useRemoveCartItemMutation,
  useAddCartItemMutation,
} from '@/entities/cart';
import { useCreateOrderMutation, CREATE_ORDER_URL } from '@/entities/order';
import { useCreateRecipientMutation } from '@/entities/recipient';
import {
  useGetRateQuoteMutation,
  useInitiateCheckoutMutation,
  useCancelCheckoutMutation,
  clearPendingIdempotencyKey,
  INITIATE_CHECKOUT_URL,
} from '../api/hooks';
import { toast } from '@/shared/ui/Toaster';
import { normalizeApiError } from '@/shared/api/errors';
import {
  isQuoteExpiredError,
  isProviderRetryableError,
  isCurrencyMismatchError,
} from '../lib/errors';
import { useCheckoutStore, CheckoutStatus } from './store';
import { parseRuDate } from '@/shared/lib/date-format';
import { PHONE_FORMATS } from '@/shared/lib/phone';
import { restoreCartItems } from '../lib/cartRollback';
import { pickProviderErrorMessage } from '../lib/quoteErrorMessage';
import { mapRateQuoteResponseToQuote } from '../lib/quoteMapper';
import { acquireInflight, releaseInflight, ensureKey, resetKey } from '../lib/idempotency';

// Minimal Cyrillic → Latin transliteration (a simplified GOST 7.79 system B).
// The backend writes `fullNameLat` into shipper documents (e.g. CDEK customs
// declaration). Until a separate Latin field is added in the UI, this is
// enough — the backend may re-normalize on its own.
const RU_TO_LAT_MAP = {
  а: 'a',
  б: 'b',
  в: 'v',
  г: 'g',
  д: 'd',
  е: 'e',
  ё: 'e',
  ж: 'zh',
  з: 'z',
  и: 'i',
  й: 'i',
  к: 'k',
  л: 'l',
  м: 'm',
  н: 'n',
  о: 'o',
  п: 'p',
  р: 'r',
  с: 's',
  т: 't',
  у: 'u',
  ф: 'f',
  х: 'kh',
  ц: 'ts',
  ч: 'ch',
  ш: 'sh',
  щ: 'shch',
  ъ: '',
  ы: 'y',
  ь: '',
  э: 'e',
  ю: 'iu',
  я: 'ia',
};

function transliterateRuToLat(input) {
  if (typeof input !== 'string') return '';
  let out = '';
  for (const ch of input) {
    const lower = ch.toLowerCase();
    const mapped = RU_TO_LAT_MAP[lower];
    if (mapped == null) {
      // Latin, digits, punctuation, whitespace — passthrough
      out += ch;
      continue;
    }
    out += ch === lower ? mapped : mapped.charAt(0).toUpperCase() + mapped.slice(1);
  }
  return out;
}

/**
 * useCheckoutFlow — Cart → checkout page navigation and backend orchestrator.
 *
 * Areas of responsibility:
 *  1. **Selection sync** — selected SKUs in `/cart` into the checkout state
 *  2. **Price via quote** — trigger `getRateQuote` once a pickup is chosen
 *  3. **Initiate → Confirm pipeline** — execute atomically on pay button press
 *  4. **Cancel on abandon** — when navigating away, unfreeze the frozen cart
 *  5. **Expiry watchers** — track quote (30 min) and attempt (15 min) TTLs
 *
 * Pattern:
 *  ```jsx
 *  const flow = useCheckoutFlow();
 *  await flow.refreshQuote();        // after pickup is selected
 *  await flow.placeOrder();          // pay button
 *  ```
 */
export function useCheckoutFlow() {
  const router = useRouter();
  const { data: cart } = useGetMyCartQuery();

  const status = useCheckoutStore((s) => s.status);
  const selectedSkuIds = useCheckoutStore((s) => s.selectedSkuIds);
  const pickup = useCheckoutStore((s) => s.pickup);
  const quote = useCheckoutStore((s) => s.quote);
  const attempt = useCheckoutStore((s) => s.attempt);
  const orderId = useCheckoutStore((s) => s.orderId);
  const error = useCheckoutStore((s) => s.error);
  const recipient = useCheckoutStore((s) => s.recipient);
  const customs = useCheckoutStore((s) => s.customs);
  const selectedRecipientId = useCheckoutStore((s) => s.selectedRecipientId);

  const setSelection = useCheckoutStore((s) => s.setSelection);
  const setPickup = useCheckoutStore((s) => s.setPickup);
  const setQuote = useCheckoutStore((s) => s.setQuote);
  const clearQuote = useCheckoutStore((s) => s.clearQuote);
  const beginInitiate = useCheckoutStore((s) => s.beginInitiate);
  const setAttempt = useCheckoutStore((s) => s.setAttempt);
  const beginConfirm = useCheckoutStore((s) => s.beginConfirm);
  const setOrder = useCheckoutStore((s) => s.setOrder);
  const setPayment = useCheckoutStore((s) => s.setPayment);
  const markCancelled = useCheckoutStore((s) => s.markCancelled);
  const setError = useCheckoutStore((s) => s.setError);
  const setSelectedRecipientId = useCheckoutStore((s) => s.setSelectedRecipientId);
  const setRemovedSnapshot = useCheckoutStore((s) => s.setRemovedSnapshot);
  const clearRemovedSnapshot = useCheckoutStore((s) => s.clearRemovedSnapshot);
  const reset = useCheckoutStore((s) => s.reset);

  const [getRateQuote] = useGetRateQuoteMutation();
  const [initiateCheckout] = useInitiateCheckoutMutation();
  const [createOrder] = useCreateOrderMutation();
  const [cancelCheckout] = useCancelCheckoutMutation();
  const [removeCartItem] = useRemoveCartItemMutation();
  const [addCartItem] = useAddCartItemMutation();
  const [createRecipient] = useCreateRecipientMutation();

  /* ── Selection helpers ── */

  // Currently selected items in the cart (cross-reference selection ↔ cart)
  const selectedItems = useMemo(() => {
    const items = Array.isArray(cart?.items) ? cart.items : [];
    if (selectedSkuIds.length === 0) return items; // no selection → all
    const set = new Set(selectedSkuIds);
    return items.filter((it) => set.has(String(it.skuId)));
  }, [cart, selectedSkuIds]);

  /**
   * Backend `/cart/checkout` freezes the whole cart — partial selection is
   * not supported (Spec §7.4). If the user hasn't selected some items in
   * the cart, we have to remove them from the cart first; otherwise the
   * backend freezes everything and they all end up in the order.
   *
   * Here `prepareCart` aligns the cart with the selection by removing the
   * unselected items. If the user comes back later they have to re-add them
   * — this is a trade-off due to the backend constraint.
   */
  const prepareCart = useCallback(async () => {
    const allItems = Array.isArray(cart?.items) ? cart.items : [];
    if (allItems.length === 0) return false;
    if (selectedSkuIds.length === 0) return true; // no selection → all-checkout
    const selectedSet = new Set(selectedSkuIds);
    const toRemove = allItems.filter((it) => !selectedSet.has(String(it.skuId)));
    if (toRemove.length === 0) return true;
    // CHK-004: snapshot for rollback — if initiate/confirm fails,
    // restoreRemoved invokes addCartItem from these records.
    setRemovedSnapshot(toRemove);
    // Removing several items at once — RTKQ optimistic patches run serially,
    // but parallel HTTPs are fine.
    await Promise.all(
      toRemove.map((it) =>
        removeCartItem(it.skuId)
          .unwrap()
          .catch(() => null)
      )
    );
    return true;
  }, [cart, selectedSkuIds, removeCartItem, setRemovedSnapshot]);

  /**
   * On initiate/confirm failure, restores the items in the `prepareCart`
   * snapshot back to the cart. Serial — sending many addCartItem requests
   * at once can cause backend rate-limiting or quantity drift inside an
   * order (best-effort, individual failures are silently preserved).
   *
   * On completion `clearRemovedSnapshot()` is called — clean slate for
   * the next attempt.
   */
  const restoreRemoved = useCallback(async () => {
    const snap = useCheckoutStore.getState().removedItemsSnapshot;
    await restoreCartItems(snap, addCartItem);
    clearRemovedSnapshot();
  }, [addCartItem, clearRemovedSnapshot]);

  /* ── Quote pipeline ── */

  // CHK-024 latest-wins: cancels the previously inflight quote request
  // (if the user switches PVZ quickly, only the latest response is kept).
  // The object returned by an RTKQ mutation trigger has `.abort()`.
  const inflightQuoteRef = useRef(null);

  /**
   * Called automatically after a pickup-point is selected (or manually).
   * Spec §8.2: weight/origin/destination are server-trusted.
   *
   * `overrides.serviceCode` — for selecting a fallbackAlternatives tariff
   * (toggle); if null/undefined the provider returns the cheapest tariff.
   */
  const refreshQuote = useCallback(
    async (overrides = {}) => {
      if (!pickup?.externalId || !pickup?.providerCode) {
        setError({ code: 'PICKUP_REQUIRED', message: 'Выберите пункт выдачи' });
        return null;
      }
      // CHK-018 Layer A: skip if cart RTKQ hasn't responded yet —
      // selectedItems can appear empty and produce a false-positive
      // "Корзина пуста" toast. Once cart loads, the `useCallback` deps update
      // (`cart` ref changes) → the QUOTING effect re-invokes refreshQuote.
      if (cart === undefined) return null;
      const itemsForQuote = selectedItems
        .map((it) => ({
          skuId: String(it.skuId),
          quantity: Math.max(1, Math.floor(Number(it.quantity || 1))),
        }))
        .filter((x) => x.skuId);
      if (itemsForQuote.length === 0) {
        setError({ code: 'EMPTY_CART', message: 'Корзина пуста' });
        return null;
      }
      // Tariff selection (fallbackAlternatives): explicit
      // `overrides.serviceCode` wins; otherwise auto-refresh preserves the
      // current `quote.serviceCode`.
      const serviceCode =
        typeof overrides?.serviceCode === 'string' && overrides.serviceCode
          ? overrides.serviceCode
          : (quote?.serviceCode ?? null);
      // Cancel the previous inflight — RTKQ returns `AbortError`, the catch
      // below ignores it via `name === 'AbortError'` (`clearQuote` is not
      // called, status stays QUOTING waiting for the next refreshQuote that
      // is about to arrive).
      if (inflightQuoteRef.current?.abort) {
        try {
          inflightQuoteRef.current.abort();
        } catch {
          // ignore
        }
      }
      const pendingPromise = getRateQuote({
        items: itemsForQuote,
        providerCode: pickup.providerCode,
        pickupPointExternalId: pickup.externalId,
        serviceCode: serviceCode ?? null,
      });
      inflightQuoteRef.current = pendingPromise;
      try {
        const resp = await pendingPromise.unwrap();
        // REFACT-001: wire shape is camelCase. The mapping layer lives in
        // `quoteMapper` — a pure helper covered by separate unit tests.
        const next = mapRateQuoteResponseToQuote(resp);
        if (!next) {
          setError({ code: 'INVALID_QUOTE_RESPONSE', message: 'Не удалось рассчитать доставку' });
          clearQuote();
          return null;
        }
        setQuote(next);
        return next;
      } catch (err) {
        // Latest-wins abort: the next refreshQuote is already in flight —
        // the UI stays in QUOTING, no error/clearQuote is called.
        if (err?.name === 'AbortError' || err?.error?.name === 'AbortError') {
          return null;
        }
        const norm = normalizeApiError(err);
        // CHK-017: call clearQuote on every quote error — status returns to
        // SELECTING_PICKUP, the UI doesn't get stuck on "Рассчитывается…".
        // The user can tap the pickup tile again and choose a different PVZ.
        clearQuote();
        if (isQuoteExpiredError(err)) {
          setError({ code: 'QUOTE_EXPIRED', message: 'Срок котировки истёк' });
        } else if (isProviderRetryableError(err)) {
          // The backend sometimes returns the technical detail
          // "Provider 'X' has no default_origin configured" —
          // pickProviderErrorMessage turns it into a user-friendly text
          // (full i18n is a separate ticket).
          setError({
            code: norm.code || 'PROVIDER_ERROR',
            message: pickProviderErrorMessage(norm.message),
          });
        } else {
          setError({
            code: norm.code,
            message: norm.message || 'Не удалось рассчитать доставку',
          });
        }
        return null;
      } finally {
        if (inflightQuoteRef.current === pendingPromise) {
          inflightQuoteRef.current = null;
        }
      }
    },
    [pickup, selectedItems, cart, quote, getRateQuote, setQuote, clearQuote, setError]
  );

  // LATEST callback in ref — to invoke placeOrder retry and the
  // auto-refresh timer without a stale closure.
  const refreshQuoteRef = useRef(refreshQuote);
  useEffect(() => {
    refreshQuoteRef.current = refreshQuote;
  }, [refreshQuote]);

  // Auto-quote when pickup updates (idempotent — doesn't resend on cache
  // hit, but an RTKQ mutation produces a fresh quote ID each time). This
  // is a simple implementation; a debounce could be added for production.
  useEffect(() => {
    if (status !== CheckoutStatus.QUOTING) return;
    refreshQuote();
    // refreshQuote itself calls `setQuote → READY` or returns an error
  }, [status, refreshQuote]);

  // When cart content/quantity changes — the quote is stale (backend
  // computes by SKU weight). Auto re-quote for a pickup in the READY state.
  // Skip on initial render — `lastCartHashRef` keeps the first value and
  // reacts to actual subsequent changes.
  const cartHash = useMemo(
    () =>
      selectedItems
        .map((it) => `${it?.skuId ?? ''}:${Math.max(1, Math.floor(Number(it?.quantity || 1)))}`)
        .join(','),
    [selectedItems]
  );
  const lastCartHashRef = useRef(cartHash);
  useEffect(() => {
    if (lastCartHashRef.current === cartHash) return;
    lastCartHashRef.current = cartHash;
    if (status === CheckoutStatus.READY && pickup?.externalId) {
      refreshQuoteRef.current?.();
    }
  }, [cartHash, status, pickup?.externalId]);

  /* ── Recipient resource resolution ── */

  /**
   * Prepares the recipient resource:
   *  • If `selectedRecipientId` already exists — returns it
   *  • Otherwise calls `POST /api/v1/recipients` to create a new resource
   *
   * Backend `CreateRecipientRequest` requires both the UI form and customs
   * to be fully filled. The UI collects these fields in two forms
   * (recipient sheet + customs sheet) — here we gather them from the store
   * and validate.
   *
   * Latin name `fullNameLat` — the UI currently naively transliterates from
   * the entered full name. Ideally the user would enter Latin in a separate
   * field (TODO P1.UI).
   */
  const ensureRecipient = useCallback(async () => {
    if (selectedRecipientId) return selectedRecipientId;

    if (!recipient || !customs) {
      setError({
        code: 'RECIPIENT_REQUIRED',
        message: 'Заполните данные получателя и таможенные реквизиты',
      });
      return null;
    }

    const fullNameRu = String(recipient.fullName || '').trim();
    const phoneRaw = String(recipient.phoneDigits || '').replace(/\D/g, '');
    const country = recipient.country || 'RU';
    const phoneFormat = PHONE_FORMATS[country] || PHONE_FORMATS.RU;
    const email = String(recipient.email || '').trim();
    const passportSerial = String(customs.passportSeries || '').replace(/\D/g, '');
    const passportNumber = String(customs.passportNumber || '').replace(/\D/g, '');
    // The UI stores dates as `DD.MM.YYYY` (CHK-001) — backend expects ISO.
    const passportIssueDate = parseRuDate(customs.issueDate);
    const birthDate = parseRuDate(customs.birthDate);
    const inn = String(customs.inn || '').replace(/\D/g, '');

    if (
      !fullNameRu ||
      phoneRaw.length !== phoneFormat.lenAfter ||
      !email ||
      passportSerial.length !== 4 ||
      passportNumber.length !== 6 ||
      !passportIssueDate ||
      !birthDate ||
      inn.length !== 12
    ) {
      setError({
        code: 'RECIPIENT_INVALID',
        message: 'Заполните все поля получателя и паспортные данные',
      });
      return null;
    }

    // Minimal Russian → Latin transliteration. Backend writes `fullNameLat`
    // into shipper documents; until a separate Latin field is added in the
    // UI, this fallback is sufficient (the backend may re-normalize itself).
    const fullNameLat = transliterateRuToLat(fullNameRu);

    try {
      const resp = await createRecipient({
        fullNameRu,
        fullNameLat,
        phone: `${phoneFormat.prefix}${phoneRaw}`,
        email,
        passportSerial,
        passportNumber,
        passportIssueDate,
        birthDate,
        inn,
      }).unwrap();
      const id = resp?.recipientId;
      if (!id) {
        setError({
          code: 'RECIPIENT_CREATE_FAILED',
          message: 'Не удалось сохранить данные получателя',
        });
        return null;
      }
      setSelectedRecipientId(id);
      return id;
    } catch (err) {
      const norm = normalizeApiError(err);
      setError({
        code: norm.code || 'RECIPIENT_CREATE_FAILED',
        message: norm.message || 'Не удалось сохранить данные получателя',
      });
      return null;
    }
  }, [recipient, customs, selectedRecipientId, createRecipient, setSelectedRecipientId, setError]);

  /* ── Place order (initiate → confirm pipeline) ── */

  /**
   * Atomic order placement (CHK-024 — with POST /orders):
   *  1. prepareCart (if partial selection, remove the unselected)
   *  2. ensureRecipient — if missing, POST /recipients
   *  3. /cart/checkout {pickupPointId, pickupCarrier, recipientId} → attempt + snapshot
   *  4. /orders {cartId, snapshotId, idempotencyKey, deliveryQuoteId, paymentProvider}
   *     → orderId + paymentIntentId + clientSecret + totalAmount
   *  5. router.push to success (via `onConfirmed` to profile/orders)
   *
   * On the failure path /cart/checkout/cancel is not called — the backend
   * snapshot expires on its own (15 min TTL) and the cart is unfrozen.
   *
   * `ORDER_DELIVERY_QUOTE_EXPIRED` (422) — quote 30 min TTL has expired,
   * but the snapshot is still alive (15 min): one-shot auto-refresh and
   * createOrder retry. The pickup selection doesn't change.
   */
  // CHK-006: Protection against pay double-tap. `inflightRef` silently
  // rejects parallel calls; `idempotencyKeyRef` provides the same header
  // on retry and resets on success (a new attempt gets a new key).
  const inflightRef = useRef(false);
  const idempotencyKeyRef = useRef(null);

  const placeOrder = useCallback(async () => {
    if (!pickup?.externalId || !pickup?.providerCode) {
      setError({ code: 'PICKUP_REQUIRED', message: 'Выберите пункт выдачи' });
      return null;
    }
    if (!quote?.quoteId) {
      setError({ code: 'QUOTE_REQUIRED', message: 'Рассчитайте стоимость доставки' });
      return null;
    }
    const cartId = cart?.id;
    if (!cartId) {
      setError({ code: 'EMPTY_CART', message: 'Корзина пуста' });
      return null;
    }

    if (!acquireInflight(inflightRef)) return null;

    try {
      const ready = await prepareCart();
      if (!ready) {
        setError({ code: 'EMPTY_CART', message: 'Корзина пуста' });
        return null;
      }

      const recipientId = await ensureRecipient();
      if (!recipientId) {
        // ensureRecipient already set the error
        return null;
      }

      const idempotencyKey = ensureKey(idempotencyKeyRef);

      beginInitiate();
      let attemptResp;
      try {
        attemptResp = await initiateCheckout({
          pickupPointId: pickup.externalId,
          pickupCarrier: pickup.providerCode,
          recipientId,
          __idempotencyKey: idempotencyKey,
        }).unwrap();
      } catch (err) {
        const norm = normalizeApiError(err);
        setError({
          code: norm.code,
          message: norm.message || 'Не удалось начать оформление',
        });
        // CHK-004: unselected items were removed in prepareCart —
        // initiate failed, restore them to the cart.
        const snapBefore = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
        await restoreRemoved();
        if (snapBefore > 0) {
          toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
        }
        return null;
      }

      setAttempt({
        attemptId: attemptResp.attemptId,
        snapshotId: attemptResp.snapshotId,
        expiresAt: attemptResp.expiresAt,
      });

      // CHK-024: inside createOrder we re-read the quote ID for retry
      // (auto-refresh may update the state).
      const tryCreate = async (deliveryQuoteId) =>
        createOrder({
          cartId,
          snapshotId: attemptResp.snapshotId,
          idempotencyKey,
          paymentProvider: 'fake',
          deliveryQuoteId,
          __idempotencyKey: idempotencyKey,
        }).unwrap();

      beginConfirm();
      let orderResp;
      try {
        orderResp = await tryCreate(quote.quoteId);
      } catch (err) {
        const norm = normalizeApiError(err);
        // ORDER_DELIVERY_QUOTE_EXPIRED — quote TTL has expired. Pickup is
        // alive, one-shot auto-refresh and retry.
        if (norm.code === 'ORDER_DELIVERY_QUOTE_EXPIRED') {
          const refreshed = await refreshQuoteRef.current?.();
          if (refreshed?.quoteId) {
            try {
              orderResp = await tryCreate(refreshed.quoteId);
            } catch (retryErr) {
              const r = normalizeApiError(retryErr);
              setError({
                code: r.code,
                message: r.message || 'Не удалось оформить заказ',
              });
              const snap = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
              await restoreRemoved();
              if (snap > 0) {
                toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
              }
              return null;
            }
          } else {
            setError({
              code: 'QUOTE_EXPIRED',
              message: 'Срок котировки истёк, рассчитайте заново',
            });
            const snap = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
            await restoreRemoved();
            if (snap > 0) {
              toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
            }
            return null;
          }
        } else {
          // ORDER_DELIVERY_QUOTE_CURRENCY_MISMATCH — backend bug: cart and
          // quote currencies differ. Shouldn't happen in the same-provider
          // case. For the UI a plain toast, warn in console (Sentry later).
          if (isCurrencyMismatchError(err)) {
            console.warn('[CHK-024] currency mismatch between cart and quote', {
              code: norm.code,
              requestId: norm.requestId,
            });
          }
          setError({
            code: norm.code,
            message: norm.message || 'Не удалось оформить заказ',
          });
          const snap = useCheckoutStore.getState().removedItemsSnapshot?.length || 0;
          await restoreRemoved();
          if (snap > 0) {
            toast.info('Не удалось оформить заказ. Товары возвращены в корзину.');
          }
          return null;
        }
      }

      const newOrderId = orderResp?.orderId ?? null;
      setPayment({
        paymentIntentId: orderResp?.paymentIntentId ?? null,
        clientSecret: orderResp?.clientSecret ?? null,
        totalAmount: orderResp?.totalAmount ?? null,
        currency: orderResp?.currency || quote.currency || 'RUB',
      });
      setOrder(newOrderId);
      // CHK-004: successful order — snapshot is no longer needed.
      clearRemovedSnapshot();
      // CHK-006: reset so that a new attempt gets a new key.
      resetKey(idempotencyKeyRef);
      clearPendingIdempotencyKey(INITIATE_CHECKOUT_URL);
      clearPendingIdempotencyKey(CREATE_ORDER_URL);
      return newOrderId;
    } finally {
      releaseInflight(inflightRef);
    }
  }, [
    pickup,
    quote,
    cart,
    prepareCart,
    ensureRecipient,
    initiateCheckout,
    createOrder,
    beginInitiate,
    setAttempt,
    beginConfirm,
    setOrder,
    setPayment,
    setError,
    restoreRemoved,
    clearRemovedSnapshot,
  ]);

  /**
   * When the user leaves the checkout page — unfreeze the frozen cart.
   * Best-effort: silent on failure (backend TTL is the guarantee in all cases).
   */
  const abandon = useCallback(async () => {
    if (status === CheckoutStatus.FROZEN || status === CheckoutStatus.CONFIRMING) {
      try {
        await cancelCheckout().unwrap();
      } catch {
        // ignore — backend TTL covers this
      }
    }
    markCancelled();
  }, [status, cancelCheckout, markCancelled]);

  /* ── Expiry watchers ── */

  // Quote 30 min TTL: auto-refresh 1 minute before expiry
  const quoteRefreshTimerRef = useRef(null);
  useEffect(() => {
    clearTimeout(quoteRefreshTimerRef.current);
    if (!quote?.expiresAt || status !== CheckoutStatus.READY) return;
    const expireMs = new Date(quote.expiresAt).getTime();
    if (!Number.isFinite(expireMs)) return;
    const refreshAt = expireMs - 60_000; // 1 min before expiry
    const delay = refreshAt - Date.now();
    if (delay <= 0) {
      refreshQuote();
      return;
    }
    quoteRefreshTimerRef.current = setTimeout(refreshQuote, delay);
    return () => clearTimeout(quoteRefreshTimerRef.current);
  }, [quote?.expiresAt, status, refreshQuote]);

  // Attempt 15 min TTL: after expiry, return status to IDLE
  const attemptExpireTimerRef = useRef(null);
  useEffect(() => {
    clearTimeout(attemptExpireTimerRef.current);
    if (!attempt?.expiresAt || status !== CheckoutStatus.FROZEN) return;
    const expireMs = new Date(attempt.expiresAt).getTime();
    if (!Number.isFinite(expireMs)) return;
    const delay = Math.max(0, expireMs - Date.now());
    attemptExpireTimerRef.current = setTimeout(() => {
      markCancelled();
      setError({
        code: 'ATTEMPT_EXPIRED',
        message: 'Срок оформления истёк, начните заново',
      });
    }, delay);
    return () => clearTimeout(attemptExpireTimerRef.current);
  }, [attempt?.expiresAt, status, markCancelled, setError]);

  /* ── Tariff alternatives ── */

  /**
   * Fallback tariff selection (one of `quote.fallbackAlternatives`).
   * Returns the status to QUOTING (`refreshQuote` does `setQuote → READY`
   * or returns an error). If equal to the current selection — no-op.
   */
  const selectServiceCode = useCallback(
    async (nextCode) => {
      if (!nextCode || typeof nextCode !== 'string') return null;
      if (quote?.serviceCode === nextCode) return quote;
      return (await refreshQuoteRef.current?.({ serviceCode: nextCode })) ?? null;
    },
    [quote]
  );

  /* ── Cross-border detection ── */

  // Spec §8.4: for cross-border items (DobroPost CN→RU) /rates/quote
  // returns only the last-mile price — the international portion of the
  // delivery is computed manually by a manager after the order.
  const hasCrossBorderItems = useMemo(
    () => selectedItems.some((it) => it?.supplierType === 'cross_border'),
    [selectedItems]
  );

  /* ── Navigation helpers ── */

  /**
   * Called from `/cart`: saves the SKU selection and navigates to `/checkout`.
   * Pickup is written to the store, not to `searchParams`.
   */
  const goToCheckout = useCallback(
    (skuIds) => {
      if (Array.isArray(skuIds) && skuIds.length === 0) return;
      setSelection(skuIds || []);
      router.push('/checkout');
    },
    [setSelection, router]
  );

  /**
   * On a successful order — to the success screen.
   * Currently the Orders module doesn't expose orderId (Spec §11), so
   * we return to `/cart` with a toast and reset the store.
   */
  const onConfirmed = useCallback(() => {
    const finalOrderId = orderId;
    reset();
    if (finalOrderId) {
      router.push(`/profile/orders?new=${encodeURIComponent(finalOrderId)}`);
    } else {
      router.push('/profile/orders');
    }
  }, [orderId, reset, router]);

  /* ── Helpers ── */

  const isPickupSelected = Boolean(pickup?.externalId && pickup?.providerCode);
  // We don't compute quote validity in `useMemo` — `Date.now()` is impure,
  // but its result is refreshed every render (the user fills the form in
  // under 30 minutes). The 1-minute-before auto-refresh effect refreshes
  // an old quote. The render-time check is purely for UI gating.
  const quoteExpiresAtMs = quote?.expiresAt ? new Date(quote.expiresAt).getTime() : 0;
  const isQuoteValid = Boolean(quote) && Number.isFinite(quoteExpiresAtMs) && quoteExpiresAtMs > 0;
  const canPlaceOrder =
    isPickupSelected && isQuoteValid && status === CheckoutStatus.READY && selectedItems.length > 0;

  // CHK-015: stable return reference. The previous version returned a new
  // object literal every render — if the consumer puts `flow` in a
  // useEffect dep, that's an infinite loop. Zustand actions are stable on
  // their own, and state primitives change when their value changes;
  // therefore the useMemo deps array is reliable.
  return useMemo(
    () => ({
      // state
      status,
      selectedSkuIds,
      selectedItems,
      pickup,
      quote,
      attempt,
      orderId,
      error,
      canPlaceOrder,
      isPickupSelected,
      isQuoteValid,
      hasCrossBorderItems,
      // actions
      setSelection,
      setPickup,
      refreshQuote,
      selectServiceCode,
      placeOrder,
      abandon,
      goToCheckout,
      onConfirmed,
      reset,
    }),
    [
      status,
      selectedSkuIds,
      selectedItems,
      pickup,
      quote,
      attempt,
      orderId,
      error,
      canPlaceOrder,
      isPickupSelected,
      isQuoteValid,
      hasCrossBorderItems,
      setSelection,
      setPickup,
      refreshQuote,
      selectServiceCode,
      placeOrder,
      abandon,
      goToCheckout,
      onConfirmed,
      reset,
    ]
  );
}
