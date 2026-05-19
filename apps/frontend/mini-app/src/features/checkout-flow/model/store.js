import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

import { onPickupSelected } from '@/shared/lib/events';

/**
 * Cart-flow checkout state machine.
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
 * ADR-011: customs documents moved out of Recipient into the independent
 * Passport bounded context. Cart-flow now holds `passportId` (M:N with
 * Recipient via Order). When any selected SKU is cross-border, the
 * customer must resolve a passport before `placeOrder` can succeed —
 * backend rejects otherwise with
 * `422 PASSPORT_REQUIRED_FOR_CROSS_BORDER` (see useCheckoutFlow
 * defence-in-depth + recovery branch).
 *
 * Persist contract (`lm-checkout-store`, sessionStorage): we keep the
 * customer's selections + drafts so a reload mid-checkout doesn't lose
 * progress. The transient backend state (attemptId, snapshotId,
 * frozen expiry, idempotency key, kill-switches) is intentionally
 * excluded.
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
  selectedSkuIds: [],
  pickup: null,
  quote: null,
  attempt: null,
  // Post-ADR-011 recipient is shipping-only: fullName / fullNameLat / phone / email
  // (resolved through `entities/recipient`'s reduced CreateRecipientRequest).
  recipient: null,
  // ADR-011: customs migrated to a Passport aggregate. The store holds
  // a resolved `passportId` (UUID) — set by `<PassportSheet />` /
  // `<PassportPicker />`. Required for cross-border carts.
  passportId: null,
  selectedRecipientId: null,
  promo: null,
  paymentMethod: 'sbp',
  orderId: null,
  payment: null,
  error: null,
  removedItemsSnapshot: null,
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
            },
            false,
            'markCancelled'
          ),

        /* ── Recipient / passport / promo / payment ── */
        setRecipient: (recipient) =>
          set(
            // When the recipient draft changes, the backend resource ID becomes
            // stale — the next `placeOrder` will create it again.
            { recipient, selectedRecipientId: null },
            false,
            'setRecipient'
          ),

        /**
         * ADR-011: passport selection is independent of recipient now.
         * Setting / clearing it does NOT invalidate `selectedRecipientId`
         * because they map to different aggregates server-side.
         */
        setPassportId: (passportId) => set({ passportId, error: null }, false, 'setPassportId'),
        clearPassportId: () => set({ passportId: null }, false, 'clearPassportId'),

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
        partialize: (state) => ({
          selectedSkuIds: state.selectedSkuIds,
          pickup: state.pickup,
          recipient: state.recipient,
          // ADR-011: customs replaced by passportId; whitelist updated.
          passportId: state.passportId,
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

/**
 * ADR-011 selector: true iff any item in the cart selection is
 * cross-border. Powers the conditional PASSPORT tile / sheet in the
 * cart-flow checkout. Consumers pass the canonical cart items shape
 * (`useCart().items` or `cart.items`).
 *
 * Pure helper — co-located with the store so `useCheckoutFlow` and the
 * cart-flow page share one definition.
 */
export function selectHasCrossBorderItems(items) {
  if (!Array.isArray(items)) return false;
  for (const it of items) {
    if (it?.supplierType === 'cross_border') return true;
  }
  return false;
}
