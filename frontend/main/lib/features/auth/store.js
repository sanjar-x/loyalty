import { create } from "zustand";
import { devtools, persist, createJSONStorage } from "zustand/middleware";

import { AuthStatus } from "./types";

/**
 * Zustand auth store.
 *
 * State machine: idle → loading → authenticated | error | expired | logged_out
 *
 * Persist: `status` va `user` localStorage'da saqlanadi. Full-page
 * navigation (`window.location.assign`) paytida cookie (HttpOnly) saqlanadi
 * va status darhol tiklanadi — shu tariqa `TelegramAuthBootstrap` qayta
 * `/api/auth/telegram` chaqirmaydi, `AuthGate` splash'da turmaydi.
 */
export const useAuthStore = create(
  devtools(
    persist(
      (set) => ({
        status: AuthStatus.IDLE,
        isNewUser: false,
        error: null,
        user: null, // { firstName, lastName, photoUrl, tgId }
        // Soft-verification flag — persist'dan `AUTHENTICATED` tiklanganda
        // bootstrap cookie'ni `GET /profile/me` orqali tekshirayotgan vaqtda
        // `true` bo'ladi. `AuthGate` shu payt children'ni render qilmaydi.
        isVerifying: false,

        setVerifying: (value) =>
          set({ isVerifying: Boolean(value) }, false, "setVerifying"),

        authStart: () =>
          set({ status: AuthStatus.LOADING, error: null }, false, "authStart"),

        authSuccess: ({ isNewUser = false, user = null } = {}) =>
          set(
            {
              status: AuthStatus.AUTHENTICATED,
              isNewUser,
              error: null,
              user,
              isVerifying: false,
            },
            false,
            "authSuccess",
          ),

        authFailure: (errorMessage) =>
          set(
            {
              status: AuthStatus.ERROR,
              error: errorMessage || "Unknown error",
              isVerifying: false,
            },
            false,
            "authFailure",
          ),

        sessionExpired: () =>
          set(
            { status: AuthStatus.EXPIRED, error: null, isVerifying: false },
            false,
            "sessionExpired",
          ),

        logout: () =>
          set(
            {
              status: AuthStatus.LOGGED_OUT,
              isNewUser: false,
              error: null,
              user: null,
              isVerifying: false,
            },
            false,
            "logout",
          ),
      }),
      {
        name: "lm-auth-store",
        storage: createJSONStorage(() =>
          typeof window !== "undefined" ? window.localStorage : undefined,
        ),
        // Faqat kerakli maydonlarni saqlaymiz (actionlar emas).
        partialize: (state) => ({
          status: state.status,
          user: state.user,
          isNewUser: state.isNewUser,
        }),
      },
    ),
    { name: "auth-store" },
  ),
);
