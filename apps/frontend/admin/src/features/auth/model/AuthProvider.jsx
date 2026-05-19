'use client';

import { createContext, useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

export const AuthContext = createContext(null);

// Status returned by the BFF proxy on a transient refresh failure (5xx /
// network blip). Surface it as a soft "service unavailable" toast on the
// next user interaction instead of looping fetches that all return 503.
const TRANSIENT_AUTH_STATUS = 503;
// Three retries with exponential backoff before raising `authUnavailable`.
// Total wait: ~0.5 + 1 + 2 ≈ 3.5s — long enough to cover a refresh-blip
// (proxy 5xx, brief network hiccup), short enough to not look frozen.
const RETRY_DELAYS_MS = [500, 1000, 2000];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function AuthProvider({ children }) {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authUnavailable, setAuthUnavailable] = useState(false);
  const inflightRef = useRef(false);

  const checkSession = useCallback(
    async ({ silent = false } = {}) => {
      if (inflightRef.current) return;
      inflightRef.current = true;
      try {
        // Try once, then retry on transient failures (503 / network) with
        // exponential backoff. Permanent 401 short-circuits to /login on
        // the first attempt — no point retrying when proxy already cleared
        // the cookies.
        const attempts = [0, ...RETRY_DELAYS_MS];
        let lastTransient = false;
        for (let i = 0; i < attempts.length; i += 1) {
          if (attempts[i] > 0) await sleep(attempts[i]);
          let res;
          try {
            res = await fetch('/api/auth/me');
          } catch {
            lastTransient = true;
            continue;
          }
          if (res.status === 401) {
            const data = await res.json().catch(() => null);
            const reason = data?.error?.code ?? 'session';
            router.replace(`/login?reason=${encodeURIComponent(reason)}`);
            return;
          }
          if (res.status === TRANSIENT_AUTH_STATUS) {
            lastTransient = true;
            continue;
          }
          setAuthUnavailable(false);
          const data = res.ok ? await res.json().catch(() => null) : null;
          setUser(data);
          return;
        }
        // All attempts failed transiently — keep user state, surface the
        // banner so the operator can manually retry.
        if (lastTransient && !silent) setAuthUnavailable(true);
      } finally {
        inflightRef.current = false;
        setIsLoading(false);
      }
    },
    [router],
  );

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  // Refresh session on tab focus / coming back online. Without this, an
  // admin who left their laptop sleeping for hours stays "authenticated"
  // until their first failing click — frustrating recovery path.
  useEffect(() => {
    function onVisibility() {
      if (document.visibilityState === 'visible') {
        checkSession({ silent: true });
      }
    }
    function onOnline() {
      checkSession({ silent: true });
    }
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('online', onOnline);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('online', onOnline);
    };
  }, [checkSession]);

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    }).catch(() => {});
    setUser(null);
    router.push('/login');
  }, [router]);

  const retrySession = useCallback(() => {
    setAuthUnavailable(false);
    checkSession();
  }, [checkSession]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        authUnavailable,
        retrySession,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
