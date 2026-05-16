import { create } from 'zustand';

/**
 * Telegram BackButton handler registry.
 *
 * Sahifalar o'z "orqaga" intent'ini ro'yxatdan o'tkazadi:
 *  • Bosh sahifa  — qidiruv/filtr sheet'larini yopish (`homeBack`)
 *  • Pickup sahifa — step-based orqaga: map/list → search → /checkout (`pickupBack`)
 *
 * `TelegramNavButtons` (shell'da bir marta mount) bu store'ni **reaktiv**
 * o'qiydi — handler ro'yxatdan o'tsa/olib tashlansa effect o'zi qayta ishga
 * tushadi. Ilgari bu `window.__LM_HOME_BACK__` / `window.__LM_PICKUP_BACK__`
 * global'lari + `setInterval(150)` polling orqali qilingan edi (audit:
 * frontend-main, 2026-05-15 — `Audit - Mini App Architecture`, P0 #2).
 *
 * Har bir sahifa o'z `useEffect` cleanup'ida mos `clear*` ni chaqirishi shart.
 */
export const useBackHandlerStore = create((set) => ({
  /** @type {(() => void) | null} */
  homeBack: null,
  /** @type {(() => void) | null} */
  pickupBack: null,

  setHomeBack: (fn) => set({ homeBack: typeof fn === 'function' ? fn : null }),
  clearHomeBack: () => set({ homeBack: null }),

  setPickupBack: (fn) => set({ pickupBack: typeof fn === 'function' ? fn : null }),
  clearPickupBack: () => set({ pickupBack: null }),
}));
