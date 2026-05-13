"use client";

import { create } from "zustand";
import { devtools } from "zustand/middleware";

interface CheckoutState {
  selectedItemIds: Set<string>;
  promoCode: string;
  recipientName: string;
  recipientPhone: string;
  recipientEmail: string;
  paymentMethod: "card" | "split" | null;
}

interface CartStoreState extends CheckoutState {
  toggleItemSelection: (id: string) => void;
  selectAll: (ids: string[]) => void;
  deselectAll: () => void;
  setPromoCode: (code: string) => void;
  setRecipient: (data: {
    name?: string;
    phone?: string;
    email?: string;
  }) => void;
  setPaymentMethod: (method: "card" | "split" | null) => void;
  resetCheckout: () => void;
}

const initialCheckout: CheckoutState = {
  selectedItemIds: new Set(),
  promoCode: "",
  recipientName: "",
  recipientPhone: "",
  recipientEmail: "",
  paymentMethod: null,
};

export const useCartStore = create<CartStoreState>()(
  devtools(
    (set) => ({
      ...initialCheckout,

      toggleItemSelection: (id) =>
        set((state) => {
          const next = new Set(state.selectedItemIds);
          if (next.has(id)) {
            next.delete(id);
          } else {
            next.add(id);
          }
          return { selectedItemIds: next };
        }),

      selectAll: (ids) =>
        set({ selectedItemIds: new Set(ids) }),

      deselectAll: () =>
        set({ selectedItemIds: new Set() }),

      setPromoCode: (code) =>
        set({ promoCode: code }),

      setRecipient: (data) =>
        set((state) => ({
          recipientName: data.name ?? state.recipientName,
          recipientPhone: data.phone ?? state.recipientPhone,
          recipientEmail: data.email ?? state.recipientEmail,
        })),

      setPaymentMethod: (method) =>
        set({ paymentMethod: method }),

      resetCheckout: () =>
        set({ ...initialCheckout, selectedItemIds: new Set() }),
    }),
    { name: "cart-store" },
  ),
);
