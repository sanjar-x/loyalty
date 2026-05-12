'use client';

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

import type { AuthStatus } from './types';

interface AuthState {
  status: AuthStatus;
  isNewUser: boolean;
  error: string | null;

  authStart: () => void;
  authSuccess: (opts?: { isNewUser?: boolean }) => void;
  authFailure: (error: string) => void;
  sessionExpired: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set) => ({
      status: 'idle',
      isNewUser: false,
      error: null,

      authStart: () => set({ status: 'loading', error: null }),

      authSuccess: (opts) =>
        set({
          status: 'authenticated',
          isNewUser: opts?.isNewUser ?? false,
          error: null,
        }),

      authFailure: (error) =>
        set({
          status: 'error',
          isNewUser: false,
          error,
        }),

      sessionExpired: () => set({ status: 'expired', isNewUser: false, error: null }),

      logout: () => set({ status: 'logged_out', isNewUser: false, error: null }),
    }),
    { name: 'auth-store' },
  ),
);
