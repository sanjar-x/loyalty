'use client';

import { TelegramSdkProvider } from '@/lib/features/telegram/provider';
import TelegramAuthBootstrap from '@/lib/features/auth/components/telegram-auth-bootstrap';
import AuthGate from '@/lib/features/auth/components/auth-gate';
import TelegramNavButtons from '@/components/blocks/telegram/TelegramNavButtons';

/**
 * TelegramAppShell — provider + auth bootstrap + UI control birlashtiradi.
 *
 * Bootstrap `AuthGate`dan tashqarida qoladi — aks holda hech qachon
 * ishga tushmaydi. Gate esa `children`ni faqat `AUTHENTICATED` holatida
 * render qiladi, shu tariqa RTK Query hook'lari token o'rnatilgunga qadar
 * backendga so'rov yuborolmaydi (MISSING_TOKEN 401'lar oldini olinadi).
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
