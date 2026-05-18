'use client';

import { create } from 'zustand';

/**
 * Minimal global toast store.
 *
 * Usage:
 *   import { toast } from "@/shared/ui/Toaster";
 *   toast.error("Не удалось оформить заказ");
 *   toast.success("Адрес сохранён");
 *
 * On the UI side, `<Toaster />` (`components/ui/Toaster.jsx`) is mounted in
 * the layout once and renders the toasts from the store.
 *
 * Multiple toasts may be visible at once (queue) — each has its own `id`,
 * default duration is 4 seconds. `toast.dismiss(id)` for manual dismissal.
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

/** Imperative API — can also be used outside the component context. */
export const toast = {
  info: (message, opts) => useToastStore.getState().push('info', message, opts),
  success: (message, opts) => useToastStore.getState().push('success', message, opts),
  error: (message, opts) => useToastStore.getState().push('error', message, opts),
  dismiss: (id) => useToastStore.getState().dismiss(id),
  clear: () => useToastStore.getState().clear(),
};
