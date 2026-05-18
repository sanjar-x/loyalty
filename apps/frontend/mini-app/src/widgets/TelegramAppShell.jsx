'use client';

import { TelegramSdkProvider } from '@/entities/user';
import { TelegramAuthBootstrap } from '@/features/auth-telegram';
import { AuthGate } from '@/features/auth-telegram';
import TelegramNavButtons from '@/widgets/TelegramNavButtons';

/**
 * TelegramAppShell — combines provider + auth bootstrap + UI control.
 *
 * Bootstrap stays outside of `AuthGate` — otherwise it would never run.
 * The gate, in turn, renders `children` only in the `AUTHENTICATED` state,
 * so RTK Query hooks cannot send requests to the backend until a token is
 * set (this prevents MISSING_TOKEN 401s).
 */
export default function TelegramAppShell({ children }) {
  return (
    <TelegramSdkProvider>
      <TelegramAuthBootstrap />
      <TelegramNavButtons />
      <AuthGate>{children}</AuthGate>
    </TelegramSdkProvider>
  );
}
