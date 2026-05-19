'use client';

import { TelegramSdkProvider } from '@/entities/user';
import { TelegramAuthBootstrap } from '@/features/auth-telegram';
import { AuthGate } from '@/features/auth-telegram';
import { GlobalBuyNowSheet } from '@/features/buy-now-checkout';
import TelegramNavButtons from '@/widgets/TelegramNavButtons';

/**
 * TelegramAppShell — combines provider + auth bootstrap + UI control.
 *
 * Bootstrap stays outside of `AuthGate` — otherwise it would never run.
 * The gate, in turn, renders `children` only in the `AUTHENTICATED` state,
 * so RTK Query hooks cannot send requests to the backend until a token is
 * set (this prevents MISSING_TOKEN 401s).
 *
 * `GlobalBuyNowSheet` is mounted once here so any consumer can open the
 * Buy Now flow with `useBuyNowStore.getState().open(...)` without having
 * to render the sheet themselves. Sits inside `AuthGate` because every
 * step of the flow requires an authenticated identity.
 */
export default function TelegramAppShell({ children }) {
  return (
    <TelegramSdkProvider>
      <TelegramAuthBootstrap />
      <TelegramNavButtons />
      <AuthGate>
        {children}
        <GlobalBuyNowSheet />
      </AuthGate>
    </TelegramSdkProvider>
  );
}
