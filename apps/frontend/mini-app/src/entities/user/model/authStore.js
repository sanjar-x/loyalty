import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

import { setAuthStatusGetter } from '@/shared/api/base-api/authStatus';
import { AuthStatus } from './authStatus';

/**
 * Zustand auth store.
 *
 * Sprint 3c: lifted from features/auth-telegram into entities/user — this
 * is the user entity (its auth state). features/auth-telegram still
 * implements the flow (Telegram initData → POST /api/auth/telegram → set
 * status), but the store itself lives here so features/favorites and others
 * can read it without a cross-feature violation.
 *
 * State machine: idle → loading → authenticated | error | expired | logged_out
 *
 * Persist: `status` and `user` in localStorage. Full-page navigation (the
 * HttpOnly cookie is preserved) — status is restored instantly, AuthGate
 * does not show the splash, and bootstrap does not re-issue /api/auth/telegram.
 */
export const useAuthStore = create(
  devtools(
    persist(
      (set) => ({
        status: AuthStatus.IDLE,
        isNewUser: false,
        error: null,
        user: null,
        isVerifying: false,

        setVerifying: (value) => set({ isVerifying: Boolean(value) }, false, 'setVerifying'),

        authStart: () => set({ status: AuthStatus.LOADING, error: null }, false, 'authStart'),

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
            'authSuccess'
          ),

        authFailure: (errorMessage) =>
          set(
            {
              status: AuthStatus.ERROR,
              error: errorMessage || 'Unknown error',
              isVerifying: false,
            },
            false,
            'authFailure'
          ),

        sessionExpired: () =>
          set(
            { status: AuthStatus.EXPIRED, error: null, isVerifying: false },
            false,
            'sessionExpired'
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
            'logout'
          ),
      }),
      {
        name: 'lm-auth-store',
        storage: createJSONStorage(() =>
          typeof window !== 'undefined' ? window.localStorage : undefined
        ),
        partialize: (state) => ({
          status: state.status,
          user: state.user,
          isNewUser: state.isNewUser,
        }),
      }
    ),
    { name: 'auth-store' }
  )
);

// Register the status getter for the baseApi DI seam (Sprint 3a).
setAuthStatusGetter(() => useAuthStore.getState().status);
