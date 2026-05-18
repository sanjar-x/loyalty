import { create } from 'zustand';

/**
 * Telegram BackButton handler registry.
 *
 * Pages register their "back" intent:
 *  • Home page   — close search/filter sheets (`homeBack`)
 *  • Pickup page — step-based back: map/list → search → /checkout (`pickupBack`)
 *
 * `TelegramNavButtons` (mounted once in the shell) reads this store
 * **reactively** — when a handler is registered/removed the effect re-runs by
 * itself. Previously this was done through `window.__LM_HOME_BACK__` /
 * `window.__LM_PICKUP_BACK__` globals + `setInterval(150)` polling (audit:
 * frontend-main, 2026-05-15 — `Audit - Mini App Architecture`, P0 #2).
 *
 * Every page must call the corresponding `clear*` in its `useEffect` cleanup.
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
