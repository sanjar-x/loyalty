'use client';

import { create } from 'zustand';

/**
 * Minimal global toast store.
 *
 * Usage:
 *   import { toast } from "@/lib/ui/toast";
 *   toast.error("Не удалось оформить заказ");
 *   toast.success("Адрес сохранён");
 *
 * UI tomondan `<Toaster />` (`components/ui/Toaster.jsx`) layoutga bir marta
 * mount qilinadi va store'dagi toast'larni ko'rsatadi.
 *
 * Bittadan ko'p toast bir vaqtda ko'rinishi mumkin (queue) — har biri o'z
 * `id`'siga ega, default duration 4 soniya. `toast.dismiss(id)` qo'lda
 * yopish uchun.
 */

let nextId = 0;

function genId() {
  nextId = (nextId + 1) % Number.MAX_SAFE_INTEGER;
  return `t_${Date.now().toString(36)}_${nextId.toString(36)}`;
}

export const useToastStore = create((set, get) => ({
  /** @type {{ id: string, type: 'info'|'success'|'error', message: string, durationMs: number }[]} */
  toasts: [],

  push: (type, message, opts = {}) => {
    const id = genId();
    const durationMs = Number.isFinite(opts.durationMs) ? Math.max(1000, opts.durationMs) : 4000;
    set((s) => ({
      toasts: [...s.toasts, { id, type, message: String(message ?? ''), durationMs }],
    }));

    if (typeof window !== 'undefined') {
      window.setTimeout(() => {
        get().dismiss(id);
      }, durationMs);
    }
    return id;
  },

  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  clear: () => set({ toasts: [] }),
}));

/** Imperative API — komponent context'idan tashqarida ham ishlatish mumkin. */
export const toast = {
  info: (message, opts) => useToastStore.getState().push('info', message, opts),
  success: (message, opts) => useToastStore.getState().push('success', message, opts),
  error: (message, opts) => useToastStore.getState().push('error', message, opts),
  dismiss: (id) => useToastStore.getState().dismiss(id),
  clear: () => useToastStore.getState().clear(),
};
