import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

import { onPickupSelected } from '@/shared/lib/events';

/**
 * Checkout state machine.
 *
 * State diagram:
 *
 *   IDLE → SELECTING_PICKUP → QUOTING → READY → INITIATING → FROZEN
 *      ↑                                                       │
 *      └────────────── CANCELLED / CONFIRMED ──────────────────┘
 *
 *  • IDLE             — not at checkout or cart is empty
 *  • SELECTING_PICKUP — user is selecting a PVZ
 *  • QUOTING          — `/logistics/rates/quote` in progress
 *  • READY            — quote received, user may press the pay button
 *  • INITIATING       — `/cart/checkout` is being called
 *  • FROZEN           — backend returned `attemptId`, waiting for payment
 *  • CONFIRMING       — `/orders` is being called (CHK-024 — instead of the
 *                       old `/cart/checkout/confirm`, together with
 *                       deliveryQuoteId)
 *  • CONFIRMED        — `orderId` returned (page navigates)
 *  • CANCELLED        — `/cart/checkout/cancel` succeeded (or TTL expired)
 *
 * Persist: only `selectedSkuIds` is stored (so the user's selection isn't lost
 * on reload). `attemptId / snapshotId / expiresAt` are **not persisted** —
 * the frozen state is valid only within this tab/session.
 */

export const CheckoutStatus = Object.freeze({
  IDLE: 'idle',
  SELECTING_PICKUP: 'selecting_pickup',
  QUOTING: 'quoting',
  READY: 'ready',
  INITIATING: 'initiating',
  FROZEN: 'frozen',
  CONFIRMING: 'confirming',
  CONFIRMED: 'confirmed',
  CANCELLED: 'cancelled',
});

const initialState = {
  status: CheckoutStatus.IDLE,
  // Cart selection (SKUs the user picked in `/cart`)
  selectedSkuIds: [],
  // Pickup-point (after the user selects a PVZ)
  pickup: null, // { externalId, providerCode, address, lat?, lon?, name?, deliveryType? }
  // Quote (result of logistics/rates/quote)
  quote: null, // { quoteId, deliveryAmount, currency, deliveryDaysMin, deliveryDaysMax, expiresAt }
  // Checkout attempt (result of cart/checkout)
  attempt: null, // { attemptId, snapshotId, expiresAt }
  // Recipient — UI draft. `fullName` is the full name (Cyrillic or Latin),
  // `phoneDigits` are operator digits (excluding the country prefix), `country`
  // is one of the CIS countries (RU/BY/KZ/UZ/UA), default "RU".
  // `email` is optional (backend requires it but we keep a fallback so the user
  // doesn't have to enter it on step 0).
  // The backend `recipientId` (UUID) lives in `selectedRecipientId`, and in
  // `placeOrder` that ID is sent; if absent, `placeOrder` creates a new resource
  // via ensureRecipient and stores its id.
  recipient: null,
  // Required for cross-border goods: passport series/number (RF), issue date,
  // birth date, INN. Part of the backend `CreateRecipientRequest`.
  customs: null,
  // ID of the recipient resource created by the backend. Must exist by the time
  // `placeOrder` initiate is called.
  selectedRecipientId: null,
  // Promo: { code, discountRub }
  promo: null,
  // Payment method ("sbp" | "card"). No card details are stored —
  // card payment is deferred to the payment provider widget (PCI DSS).
  paymentMethod: 'sbp',
  // Final order
  orderId: null,
  // CHK-024: payment metadata from the POST /orders response. `clientSecret`
  // is an opaque value passed to the provider widget (Stripe-like).
  payment: null, // { paymentIntentId, clientSecret, totalAmount, currency }
  // Error (envelope code or message)
  error: null,
  // CHK-004: snapshot of CartItemResponse for items prepareCart removed from
  // the cart (the unselected SKUs). Used to restore on initiate/confirm fail.
  // Transient — lost when the page closes (we don't get the backend TTL,
  // this is UX compensation).
  removedItemsSnapshot: null,
  // Sprint 3e: pvzAccumCache has been moved to entities/pickup-point/model/pvzAccumStore.
};

export const useCheckoutStore = create(
  devtools(
    persist(
      (set) => ({
        ...initialState,

        /* ── Selection (cart → checkout transition) ── */
        setSelection: (skuIds) =>
          set(
            {
              selectedSkuIds: Array.isArray(skuIds)
                ? skuIds.filter((id) => typeof id === 'string' && id)
                : [],
              error: null,
            },
            false,
            'setSelection'
          ),

        /* ── Pickup picker ── */
        beginPickupSelection: () =>
          set(
            {
              status: CheckoutStatus.SELECTING_PICKUP,
              pickup: null,
              quote: null,
              error: null,
            },
            false,
            'beginPickupSelection'
          ),

        setPickup: (pickup) =>
          set(
            (state) => {
              // CHK-015 defense-in-depth: if the pickup is identical and the
              // status is already QUOTING/READY — no-op. The deps fix in
              // page.jsx is enough, but if called from elsewhere there's no loop.
              const prev = state.pickup;
              const stableStatus =
                state.status === CheckoutStatus.QUOTING || state.status === CheckoutStatus.READY;
              const isSame =
                prev &&
                prev.externalId === pickup?.externalId &&
                prev.providerCode === pickup?.providerCode &&
                prev.address === pickup?.address &&
                prev.lat === pickup?.lat &&
                prev.lon === pickup?.lon &&
                stableStatus;
              if (isSame) return state;
              // CHK-024: different pickup points → different tariffs. The old quote
              // (and its serviceCode/fallbackAlternatives) is invalid — we
              // reset it, and refreshQuote requests the cheapest tariff from
              // a clean state.
              const isDifferentPickup =
                !prev ||
                prev.externalId !== pickup?.externalId ||
                prev.providerCode !== pickup?.providerCode;
              return {
                pickup,
                quote: isDifferentPickup ? null : state.quote,
                status: CheckoutStatus.QUOTING,
                error: null,
              };
            },
            false,
            'setPickup'
          ),

        /* ── Quote ── */
        setQuote: (quote) =>
          set(
            (state) => {
              // CHK-015: idempotent — if the same quoteId is written again, no-op.
              const prev = state.quote;
              if (
                prev &&
                prev.quoteId === quote?.quoteId &&
                state.status === CheckoutStatus.READY
              ) {
                return state;
              }
              return {
                quote,
                status: CheckoutStatus.READY,
                error: null,
              };
            },
            false,
            'setQuote'
          ),

        clearQuote: () =>
          set(
            (s) => ({
              quote: null,
              status:
                s.status === CheckoutStatus.READY || s.status === CheckoutStatus.QUOTING
                  ? CheckoutStatus.SELECTING_PICKUP
                  : s.status,
            }),
            false,
            'clearQuote'
          ),

        /* ── Initiate / confirm / cancel ── */
        beginInitiate: () =>
          set({ status: CheckoutStatus.INITIATING, error: null }, false, 'beginInitiate'),

        setAttempt: (attempt) =>
          set(
            (state) => {
              // CHK-015: idempotent.
              if (
                state.attempt &&
                state.attempt.attemptId === attempt?.attemptId &&
                state.status === CheckoutStatus.FROZEN
              ) {
                return state;
              }
              return { attempt, status: CheckoutStatus.FROZEN };
            },
            false,
            'setAttempt'
          ),

        beginConfirm: () =>
          set({ status: CheckoutStatus.CONFIRMING, error: null }, false, 'beginConfirm'),

        setOrder: (orderId) =>
          set(
            (state) => {
              // CHK-015: idempotent — if the onConfirmed effect lands here a
              // second time, no re-render is triggered.
              if (state.orderId === orderId && state.status === CheckoutStatus.CONFIRMED) {
                return state;
              }
              return { orderId, status: CheckoutStatus.CONFIRMED };
            },
            false,
            'setOrder'
          ),

        setPayment: (payment) => set({ payment }, false, 'setPayment'),

        markCancelled: () =>
          set(
            {
              ...initialState,
              status: CheckoutStatus.CANCELLED,
              // We don't preserve selectedSkuIds — if the user returns they re-select
            },
            false,
            'markCancelled'
          ),

        /* ── Recipient / customs / promo / payment ── */
        setRecipient: (recipient) =>
          set(
            // When the recipient draft changes, the backend resource ID becomes
            // stale — the next `placeOrder` will create it again.
            { recipient, selectedRecipientId: null },
            false,
            'setRecipient'
          ),
        setCustoms: (customs) => set({ customs, selectedRecipientId: null }, false, 'setCustoms'),
        setSelectedRecipientId: (selectedRecipientId) =>
          set({ selectedRecipientId }, false, 'setSelectedRecipientId'),
        setPromo: (promo) => set({ promo }, false, 'setPromo'),
        setPaymentMethod: (paymentMethod) =>
          set(
            { paymentMethod: paymentMethod === 'card' ? 'card' : 'sbp' },
            false,
            'setPaymentMethod'
          ),

        /* ── Removed-items snapshot (CHK-004 rollback) ── */
        setRemovedSnapshot: (items) =>
          set(
            {
              removedItemsSnapshot: Array.isArray(items) && items.length > 0 ? items : null,
            },
            false,
            'setRemovedSnapshot'
          ),
        clearRemovedSnapshot: () =>
          set({ removedItemsSnapshot: null }, false, 'clearRemovedSnapshot'),

        /* ── Error / reset ── */
        setError: (error) => set({ error }, false, 'setError'),

        reset: () => set({ ...initialState }, false, 'reset'),
      }),
      {
        name: 'lm-checkout-store',
        storage: createJSONStorage(() =>
          typeof window !== 'undefined' ? window.sessionStorage : undefined
        ),
        // Only the user's selection and required draft fields — we don't
        // persist the backend attemptId or the frozen-state (there's a TTL,
        // on re-open the backend must freeze again).
        partialize: (state) => ({
          selectedSkuIds: state.selectedSkuIds,
          pickup: state.pickup,
          recipient: state.recipient,
          customs: state.customs,
          promo: state.promo,
          paymentMethod: state.paymentMethod,
          selectedRecipientId: state.selectedRecipientId,
        }),
      }
    ),
    { name: 'checkout-store' }
  )
);

// Sprint 3e: pickup-selection emits pickup → checkout store applies it
// (FSM action setPickup). Breaks the cross-feature dep:
// pickup-selection now knows only about shared/lib/events.
if (typeof window !== 'undefined') {
  onPickupSelected((pickup) => {
    useCheckoutStore.getState().setPickup(pickup);
  });
}
