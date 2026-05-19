'use client';

import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

/**
 * Buy-now checkout FSM (parallel to cart-flow's `useCheckoutStore`, NOT
 * a generalisation — see audit FE-4).
 *
 * Backed by:
 *  • ADR-010 (apps/backend/docs/ADR-010-buy-now-standalone-endpoint.md)
 *    — I1 (cart not modified) + I2 (recipient resolved inline before
 *    POST /orders/buy-now).
 *  • ADR-011 (apps/backend/docs/ADR-011-passport-as-independent-bounded-context.md)
 *    — Passport is an independent bounded context. CROSS_BORDER items
 *    require a `passportId` on the request; backend rejects the order
 *    with 422 `PASSPORT_REQUIRED_FOR_CROSS_BORDER` otherwise. The FSM
 *    inserts a PASSPORT step between RECIPIENT and PICKUP for those SKUs
 *    and skips it entirely for LOCAL items.
 *
 * State machine (LOCAL supplier):
 *
 *   IDLE → SKU → RECIPIENT → PICKUP → CONFIRM → SUBMITTING → SUCCESS
 *                                                       ↓
 *                                                     ERROR ─→ CONFIRM
 *
 * State machine (CROSS_BORDER supplier):
 *
 *   IDLE → SKU → RECIPIENT → PASSPORT → PICKUP → CONFIRM → SUBMITTING
 *                                                              ↓
 *                                                            SUCCESS / ERROR
 *
 *  • IDLE       — sheet closed
 *  • SKU        — sheet just opened; shows product summary + qty
 *  • RECIPIENT  — pick existing recipient or create new (inline form)
 *  • PASSPORT   — (cross-border only) pick existing passport or create
 *                 new via features/passport-form. Required for the
 *                 customs declaration; LOCAL flow skips this step.
 *  • PICKUP     — inline pickup-selector; triggers /rates/quote
 *  • CONFIRM    — totals review; pay button enabled
 *  • SUBMITTING — POST /orders/buy-now in flight
 *  • SUCCESS    — 201 received; route to /orders/{id} (or PSP stub)
 *  • ERROR      — recoverable; UI surfaces toast + offers retry
 *
 * Persist contract (lm-buy-now-store, sessionStorage):
 *  - PERSIST: status, skuId, quantity, productMeta, recipientId,
 *             passportId, pickup
 *  - SKIP:    quote (TTL-bound, refetched), idempotencyKey (per-attempt),
 *             orderId / payment / error, disabledReason / disabledUntil
 *             (Sprint 1.5 kill-switch must self-probe on a new session).
 */

export const BuyNowStep = Object.freeze({
  IDLE: 'idle',
  SKU: 'sku',
  RECIPIENT: 'recipient',
  PASSPORT: 'passport',
  PICKUP: 'pickup',
  CONFIRM: 'confirm',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
});

/**
 * Kill-switch lockout window applied after a `BUY_NOW_DISABLED` 503
 * response. ProductPage / QuickAddSheet grey out the «Купить сейчас»
 * button until the deadline; the store auto-clears the flag on read
 * once `Date.now() > disabledUntil`.
 */
export const BUY_NOW_DISABLED_TTL_MS = 5 * 60 * 1000;

/**
 * ADR-011 — passport is required on the request when any SKU in the
 * order is cross-border. Mini-app receives `supplierType` on
 * `StorefrontProductDetailResponse.supplier.type` (Gap A landed); we
 * compare against the lowercase form the backend emits.
 */
export const CROSS_BORDER_SUPPLIER_TYPE = 'cross_border';

export function supplierTypeRequiresPassport(supplierType) {
  return String(supplierType || '').toLowerCase() === CROSS_BORDER_SUPPLIER_TYPE;
}

const initialState = {
  status: BuyNowStep.IDLE,

  // Source — flowed from ProductPage / QuickAddSheet on open().
  // `productMeta` is read-only display info (name/image/price + supplierType)
  // so the sheet renders consistent context and the FSM branches on
  // CROSS_BORDER without a PDP refetch.
  skuId: null,
  quantity: 1,
  productMeta: null, // { name, image, priceRub, currency, variantLabel, supplierType, ... }

  // Resolved recipient (existing chosen OR newly-created id — see ADR-010 I2).
  recipientId: null,

  // Resolved customs passport (existing chosen OR newly-created id —
  // ADR-011). Stays null for LOCAL-only orders.
  passportId: null,

  // Selected pickup. Shape: { externalId, providerCode, address, lat?, lon? }
  // — mirrors features/checkout-flow's pickup so downstream consumers
  // and shared helpers (e.g. resolve_delivery_quote on the backend)
  // treat both flows identically.
  pickup: null,

  // Quote payload (deliveryQuoteId + amount + expiresAt). NOT persisted —
  // refetched after every reopen / pickup change. The mapped shape is
  // produced by `features/checkout-flow/lib/quoteMapper` which is shared
  // between cart-flow and buy-now.
  quote: null,

  // Per-attempt idempotency key. Regenerated only after SUCCESS or reset
  // — see lib/idempotencyKey.js. NOT persisted.
  idempotencyKey: null,

  // Server response after 201.
  orderId: null,
  payment: null, // { paymentIntentId, clientSecret, totalAmount, currency, autoCaptured }

  // Recoverable error envelope (normalizeApiError shape).
  error: null,

  // Kill-switch from Sprint 1.5 (`BUY_NOW_ENABLED=false` → backend returns
  // 503 with `error.code === "BUY_NOW_DISABLED"`). NOT persisted: a fresh
  // session must probe the endpoint again so the flag self-heals when
  // backend re-enables Buy Now.
  disabledReason: null, // 'BUY_NOW_DISABLED' | null
  disabledUntil: 0, // epoch ms; 0 == not disabled
};

export const useBuyNowStore = create(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        /* ── Lifecycle ── */
        open: ({ skuId, quantity, productMeta }) =>
          set(
            (state) => ({
              status:
                state.status === BuyNowStep.IDLE || state.skuId !== skuId
                  ? BuyNowStep.SKU
                  : state.status,
              skuId: skuId ?? null,
              quantity: Math.max(1, Math.min(99, Math.floor(Number(quantity) || 1))),
              productMeta: productMeta ?? null,
              error: null,
              // Drop volatile fields if the customer reopens with a
              // different SKU — old quote / order id / passport selection
              // would be invalid for the new SKU.
              ...(state.skuId !== skuId
                ? { quote: null, orderId: null, payment: null, passportId: null }
                : {}),
            }),
            false,
            'buyNow/open'
          ),

        close: () => set({ status: BuyNowStep.IDLE, error: null }, false, 'buyNow/close'),

        reset: () => set({ ...initialState }, false, 'buyNow/reset'),

        /* ── Step navigation ── */
        goToStep: (step) => set({ status: step, error: null }, false, 'buyNow/goToStep'),

        /**
         * FSM-aware forward navigation. Inserts PASSPORT between RECIPIENT
         * and PICKUP for CROSS_BORDER orders; LOCAL orders go straight
         * to PICKUP. Consumers prefer `nextStep()` over manual
         * `goToStep(...)` so the branching invariant is owned by the store.
         */
        nextStep: () => {
          const state = get();
          const crossBorder = supplierTypeRequiresPassport(state.productMeta?.supplierType);
          const map = {
            [BuyNowStep.SKU]: BuyNowStep.RECIPIENT,
            [BuyNowStep.RECIPIENT]: crossBorder ? BuyNowStep.PASSPORT : BuyNowStep.PICKUP,
            [BuyNowStep.PASSPORT]: BuyNowStep.PICKUP,
            [BuyNowStep.PICKUP]: BuyNowStep.CONFIRM,
          };
          const next = map[state.status];
          if (next) set({ status: next, error: null }, false, 'buyNow/nextStep');
        },

        prevStep: () => {
          const state = get();
          const crossBorder = supplierTypeRequiresPassport(state.productMeta?.supplierType);
          const map = {
            [BuyNowStep.CONFIRM]: BuyNowStep.PICKUP,
            [BuyNowStep.PICKUP]: crossBorder ? BuyNowStep.PASSPORT : BuyNowStep.RECIPIENT,
            [BuyNowStep.PASSPORT]: BuyNowStep.RECIPIENT,
            [BuyNowStep.RECIPIENT]: BuyNowStep.SKU,
          };
          const prev = map[state.status];
          if (prev) set({ status: prev, error: null }, false, 'buyNow/prevStep');
        },

        /* ── Field setters ── */
        setQuantity: (n) =>
          set(
            { quantity: Math.max(1, Math.min(99, Math.floor(Number(n) || 1))) },
            false,
            'buyNow/setQuantity'
          ),

        setRecipientId: (recipientId) =>
          set({ recipientId, error: null }, false, 'buyNow/setRecipientId'),

        setPassportId: (passportId) =>
          set({ passportId, error: null }, false, 'buyNow/setPassportId'),

        clearPassportId: () => set({ passportId: null }, false, 'buyNow/clearPassportId'),

        setPickup: (pickup) =>
          set(
            // Different pickup → drop stale quote so PickupStep re-fetches.
            (state) => ({
              pickup,
              quote:
                !state.pickup ||
                state.pickup.externalId !== pickup?.externalId ||
                state.pickup.providerCode !== pickup?.providerCode
                  ? null
                  : state.quote,
              error: null,
            }),
            false,
            'buyNow/setPickup'
          ),

        setQuote: (quote) => set({ quote, error: null }, false, 'buyNow/setQuote'),
        clearQuote: () => set({ quote: null }, false, 'buyNow/clearQuote'),

        setIdempotencyKey: (key) => set({ idempotencyKey: key }, false, 'buyNow/setIdempotencyKey'),

        /* ── Submit / response ── */
        beginSubmit: () =>
          set({ status: BuyNowStep.SUBMITTING, error: null }, false, 'buyNow/beginSubmit'),

        setSuccess: ({ orderId, payment }) =>
          set(
            { status: BuyNowStep.SUCCESS, orderId, payment, error: null },
            false,
            'buyNow/setSuccess'
          ),

        setError: (error) => set({ status: BuyNowStep.ERROR, error }, false, 'buyNow/setError'),

        /* ── Kill-switch (Sprint 1.5 BUY_NOW_ENABLED) ── */
        markDisabled: (reason = 'BUY_NOW_DISABLED') =>
          set(
            {
              disabledReason: reason,
              disabledUntil: Date.now() + BUY_NOW_DISABLED_TTL_MS,
            },
            false,
            'buyNow/markDisabled'
          ),

        clearDisabled: () =>
          set({ disabledReason: null, disabledUntil: 0 }, false, 'buyNow/clearDisabled'),

        /**
         * Returns `true` iff the kill-switch window is still active.
         * Self-heals: when the deadline has passed it transparently
         * clears the flag so the next probe goes through. Cheap to call
         * from selectors.
         */
        isDisabledNow: () => {
          const { disabledReason, disabledUntil } = get();
          if (!disabledReason) return false;
          if (Date.now() >= disabledUntil) {
            // Lazy expiry — no setTimeout required, the store stays
            // truthful for any reader.
            set({ disabledReason: null, disabledUntil: 0 }, false, 'buyNow/disabledExpired');
            return false;
          }
          return true;
        },
      }),
      {
        name: 'lm-buy-now-store',
        storage: createJSONStorage(() =>
          typeof window !== 'undefined' ? window.sessionStorage : undefined
        ),
        partialize: (state) => ({
          status: state.status === BuyNowStep.SUBMITTING ? BuyNowStep.CONFIRM : state.status,
          skuId: state.skuId,
          quantity: state.quantity,
          productMeta: state.productMeta,
          recipientId: state.recipientId,
          passportId: state.passportId,
          pickup: state.pickup,
          // Volatile / per-attempt / kill-switch — explicitly excluded:
          // quote, idempotencyKey, orderId, payment, error,
          // disabledReason, disabledUntil.
        }),
      }
    ),
    { name: 'buy-now-store' }
  )
);
