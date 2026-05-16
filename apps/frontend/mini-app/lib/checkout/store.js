import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

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
  // Cart selection (foydalanuvchi `/cart`'da tanlagan SKU'lar)
  selectedSkuIds: [],
  // Pickup-point (foydalanuvchi PVZ tanlagandan keyin)
  pickup: null, // { externalId, providerCode, address, lat?, lon?, name?, deliveryType? }
  // Quote (logistics/rates/quote natijasi)
  quote: null, // { quoteId, deliveryAmount, currency, deliveryDaysMin, deliveryDaysMax, expiresAt }
  // Checkout attempt (cart/checkout natijasi)
  attempt: null, // { attemptId, snapshotId, expiresAt }
  // Recipient — UI draft. `fullName` to'liq F.I.Sh. (kirilcha yoki lotin),
  // `phoneDigits` operator raqamlari (country prefix tashqarisida), `country`
  // CIS countries (RU/BY/KZ/UZ/UA), default "RU".
  // `email` opsional (backend talab qiladi, lekin user 0-step'da kirita olmasligi uchun fallback).
  // Backend `recipientId` (UUID) `selectedRecipientId`'da yashaydi va `placeOrder`'da
  // o'sha ID yuboriladi; agar yo'q bo'lsa `placeOrder` ensureRecipient orqali yangi
  // resurs yaratadi va id'sini saqlaydi.
  recipient: null,
  // Cross-border tovari uchun majburiy: passport seriya/raqam (RF), berilgan sana,
  // tug'ilgan sana, INN. Backend `CreateRecipientRequest`'ning bir qismi.
  customs: null,
  // Backend tomonidan yaratilgan recipient resurs IDsi. `placeOrder` initiate
  // chaqiriladigan kunda mavjud bo'lishi shart.
  selectedRecipientId: null,
  // Promo: { code, discountRub }
  promo: null,
  // Payment method ("sbp" | "card"). Hech qanday card detail saqlanmaydi —
  // card to'lovi payment provider widget'iga deferring qilinadi (PCI DSS).
  paymentMethod: 'sbp',
  // Yakuniy buyurtma
  orderId: null,
  // Xato (envelope code yoki message)
  error: null,
  // CHK-004: prepareCart tanlanmagan SKU'larni cart'dan o'chirgan paytdagi
  // CartItemResponse snapshot. initiate/confirm fail bo'lsa restore qilish
  // uchun ishlatiladi. Transient — sahifa yopilsa yo'qoladi (backend TTL
  // bizdan dalda emas, bu UX kompensatsiyasi).
  removedItemsSnapshot: null,
  // CHK-016 Bug #3: pickup sahifa mount paytida pvzAccum yo'qoladi → eski
  // markerlar yo'q, qayta fetch kerak. Bu yerda sessionStorage'da entries
  // shaklida saqlaymiz ([[id, point], ...]) — Map JSON-friendly emas.
  // Backend qayta fetch bo'lsa merge by id ko'p martalik yangilanadi.
  pvzAccumCache: null,
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
              // CHK-015 defense-in-depth: agar pickup identik va status
              // allaqachon QUOTING/READY bo'lsa — no-op. page.jsx'da deps
              // fix yetarli, lekin boshqa joydan chaqirilsa loop yo'q.
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
              return {
                pickup,
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
              // CHK-015: idempotent — bir xil quoteId qayta yozilsa no-op.
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
              // CHK-015: idempotent — onConfirmed effect ham bu yerga
              // ikkinchi marta tushsa, re-render trigger qilinmaydi.
              if (state.orderId === orderId && state.status === CheckoutStatus.CONFIRMED) {
                return state;
              }
              return { orderId, status: CheckoutStatus.CONFIRMED };
            },
            false,
            'setOrder'
          ),

        markCancelled: () =>
          set(
            {
              ...initialState,
              status: CheckoutStatus.CANCELLED,
              // selectedSkuIds'ni saqlamaymiz — foydalanuvchi qaytsa qayta tanlaydi
            },
            false,
            'markCancelled'
          ),

        /* ── Recipient / customs / promo / payment ── */
        setRecipient: (recipient) =>
          set(
            // Recipient draft o'zgarganda backend resurs ID'si stale bo'ladi —
            // keyingi `placeOrder` qaytadan create qiladi.
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

        /* ── PVZ accum cache (CHK-016 Bug #3) ── */
        setPvzAccumEntries: (entries) =>
          set(
            {
              pvzAccumCache: Array.isArray(entries) ? entries : null,
            },
            false,
            'setPvzAccumEntries'
          ),

        /* ── Error / reset ── */
        setError: (error) => set({ error }, false, 'setError'),

        reset: () => set({ ...initialState }, false, 'reset'),
      }),
      {
        name: 'lm-checkout-store',
        storage: createJSONStorage(() =>
          typeof window !== 'undefined' ? window.sessionStorage : undefined
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
          selectedRecipientId: state.selectedRecipientId,
          pvzAccumCache: state.pvzAccumCache,
        }),
      }
    ),
    { name: 'checkout-store' }
  )
);
