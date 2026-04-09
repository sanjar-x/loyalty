'use client';

import { createContext, useContext, type ReactNode } from 'react';

import { useTelegramSdkRuntime } from './provider-runtime';
import type { TelegramContextValue } from './provider.types';

export type { TelegramContextValue } from './provider.types';

const TelegramContext = createContext<TelegramContextValue | null>(null);

/**
 * Low-level hook for full Telegram SDK context.
 * Prefer this when infrastructure code needs direct access to `webApp` or raw SDK state.
 */
export function useTelegramContext(): TelegramContextValue {
  const context = useContext(TelegramContext);

  if (!context) {
    throw new Error(
      'useTelegramContext must be used within a <TelegramSdkProvider>. ' +
        'Wrap your app (or the relevant subtree) with <TelegramSdkProvider>.',
    );
  }

  return context;
}

export interface TelegramSdkProviderProps {
  children: ReactNode;
}

export function TelegramSdkProvider({ children }: TelegramSdkProviderProps) {
  const value = useTelegramSdkRuntime();

  return <TelegramContext.Provider value={value}>{children}</TelegramContext.Provider>;
}
