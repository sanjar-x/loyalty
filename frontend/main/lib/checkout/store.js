import { create } from "zustand";
import { devtools, persist, createJSONStorage } from "zustand/middleware";

/**
 * Checkout state machine.
 *
 * State diagram:
 *
 *   IDLE → SELECTING_PICKUP → QUOTING → READY → INITIATING → FROZEN
 *      ↑                                                       │
 *      └────────────── CANCELLED / CONFIRMED ──────────────────┘
 *
 *  • IDLE             — kassada yo'q yoki cart bo'sh
 *  • SELECTING_PICKUP — foydalanuvchi PVZ tanlamoqda
 *  • QUOTING          — `/logistics/rates/quote` jarayonida
 *  • READY            — quote olingan, foydalanuvchi pay-button bosishi mumkin
 *  • INITIATING       — `/cart/checkout` chaqirilmoqda
 *  • FROZEN           — backend `attemptId` qaytardi, payment kutilmoqda
 *  • CONFIRMING       — `/cart/checkout/confirm` chaqirilmoqda
 *  • CONFIRMED        — `orderId` qaytdi (sahifa nav qiladi)
 *  • CANCELLED        — `/cart/checkout/cancel` muvaffaqiyatli (yoki TTL tugadi)
 *
 * Persist: faqat `selectedSkuIds` saqlanadi (foydalanuvchi reload qilsa
 * tanlovi tushib qolmaydi). `attemptId / snapshotId / expiresAt`
 * **persist'da emas** — frozen state faqat shu tab/sessiyada amal qiladi.
 */

export const CheckoutStatus = Object.freeze({
  IDLE: "idle",
  SELECTING_PICKUP: "selecting_pickup",
  QUOTING: "quoting",
  READY: "ready",
  INITIATING: "initiating",
  FROZEN: "frozen",
  CONFIRMING: "confirming",
  CONFIRMED: "confirmed",
  CANCELLED: "cancelled",
});

const initialState = {
  status: CheckoutStatus.IDLE,
  // Cart selection (foydalanuvchi `/trash`'da tanlagan SKU'lar)
  selectedSkuIds: [],
  // Pickup-point (foydalanuvchi PVZ tanlagandan keyin)
  pickup: null, // { externalId, providerCode, address, name, deliveryType }
  // Quote (logistics/rates/quote natijasi)
  quote: null, // { quoteId, deliveryAmount, currency, deliveryDaysMin, deliveryDaysMax, expiresAt }
  // Checkout attempt (cart/checkout natijasi)
  attempt: null, // { attemptId, snapshotId, expiresAt }
  // Recipient: { fullName, phoneDigits, email }
  recipient: null,
  // Customs (cross-border tovari uchun): { passportSeries, passportNumber, issueDate, birthDate, inn }
  customs: null,
  // Promo: { code, discountRub }
  promo: null,
  // Payment method ("sbp" | "card"). Hech qanday card detail saqlanmaydi —
  // card to'lovi payment provider widget'iga deferring qilinadi (PCI DSS).
  paymentMethod: "sbp",
  // Yakuniy buyurtma
  orderId: null,
  // Xato (envelope code yoki message)
  error: null,
};

export const useCheckoutStore = create(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        /* ── Selection (cart → checkout transition) ── */
        setSelection: (skuIds) =>
          set(
            {
              selectedSkuIds: Array.isArray(skuIds)
                ? skuIds.filter((id) => typeof id === "string" && id)
                : [],
              error: null,
            },
            false,
            "setSelection",
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
            "beginPickupSelection",
          ),

        setPickup: (pickup) =>
          set(
            {
              pickup,
              status: CheckoutStatus.QUOTING,
              error: null,
            },
            false,
            "setPickup",
          ),

        /* ── Quote ── */
        setQuote: (quote) =>
          set(
            {
              quote,
              status: CheckoutStatus.READY,
              error: null,
            },
            false,
            "setQuote",
          ),

        clearQuote: () =>
          set(
            (s) => ({
              quote: null,
              status:
                s.status === CheckoutStatus.READY ||
                s.status === CheckoutStatus.QUOTING
                  ? CheckoutStatus.SELECTING_PICKUP
                  : s.status,
            }),
            false,
            "clearQuote",
          ),

        /* ── Initiate / confirm / cancel ── */
        beginInitiate: () =>
          set(
            { status: CheckoutStatus.INITIATING, error: null },
            false,
            "beginInitiate",
          ),

        setAttempt: (attempt) =>
          set(
            { attempt, status: CheckoutStatus.FROZEN },
            false,
            "setAttempt",
          ),

        beginConfirm: () =>
          set(
            { status: CheckoutStatus.CONFIRMING, error: null },
            false,
            "beginConfirm",
          ),

        setOrder: (orderId) =>
          set(
            { orderId, status: CheckoutStatus.CONFIRMED },
            false,
            "setOrder",
          ),

        markCancelled: () =>
          set(
            {
              ...initialState,
              status: CheckoutStatus.CANCELLED,
              // selectedSkuIds'ni saqlamaymiz — foydalanuvchi qaytsa qayta tanlaydi
            },
            false,
            "markCancelled",
          ),

        /* ── Recipient / customs / promo / payment ── */
        setRecipient: (recipient) => set({ recipient }, false, "setRecipient"),
        setCustoms: (customs) => set({ customs }, false, "setCustoms"),
        setPromo: (promo) => set({ promo }, false, "setPromo"),
        setPaymentMethod: (paymentMethod) =>
          set(
            { paymentMethod: paymentMethod === "card" ? "card" : "sbp" },
            false,
            "setPaymentMethod",
          ),

        /* ── Error / reset ── */
        setError: (error) => set({ error }, false, "setError"),

        reset: () => set({ ...initialState }, false, "reset"),
      }),
      {
        name: "lm-checkout-store",
        storage: createJSONStorage(() =>
          typeof window !== "undefined" ? window.sessionStorage : undefined,
        ),
        // Faqat foydalanuvchi tanlovi va kerakli draft maydonlar — backend
        // attemptId va frozen-state'ni persist qilmaymiz (TTL bor, qayta
        // ochilganda backend qaytadan freeze qilishi kerak).
        partialize: (state) => ({
          selectedSkuIds: state.selectedSkuIds,
          pickup: state.pickup,
          recipient: state.recipient,
          customs: state.customs,
          promo: state.promo,
          paymentMethod: state.paymentMethod,
        }),
      },
    ),
    { name: "checkout-store" },
  ),
);
