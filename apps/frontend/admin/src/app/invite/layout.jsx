'use client';

import { ToastProvider } from '@/shared/hooks/useToast';
import { QueryProvider } from '@/shared/query';

// Public route group for invitee onboarding. Deliberately does NOT mount
// `AuthProvider` — the invitee has no session yet, and AuthProvider would
// fire `GET /api/auth/me` and bounce to /login on the inevitable 401,
// breaking the accept flow before it starts.
//
// QueryProvider + ToastProvider are still useful: the validate / accept
// hooks rely on TanStack Query and the accept handler surfaces backend
// errors via toast.
export default function InviteLayout({ children }) {
  return (
    <QueryProvider>
      <ToastProvider>
        <div className="bg-app-panel flex min-h-screen w-full items-center justify-center p-5">
          {children}
        </div>
      </ToastProvider>
    </QueryProvider>
  );
}
