/**
 * Anonymous cart token storage.
 *
 * Spec: SPEC - Frontend Integration Guide §7
 *   - The guest cart ID is sent via the `X-Anonymous-Token` header. The
 *     backend issues the token from `POST /api/v1/cart/anonymous-token`.
 *   - After login, `POST /api/v1/cart/merge {anonymousToken}` is called, and
 *     at that point the token is removed (to prevent a repeated merge).
 *
 * Storage: localStorage. SSR-safe (checks for missing `window`).
 * Even though the backend stores the token for several weeks, for the
 * frontend "merge or drop it" — one of the two outcomes is enough.
 */

const STORAGE_KEY = 'lm-anonymous-cart-token';

function safeLocalStorage() {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function getAnonymousToken() {
  const ls = safeLocalStorage();
  if (!ls) return '';
  try {
    const v = ls.getItem(STORAGE_KEY);
    return typeof v === 'string' ? v : '';
  } catch {
    return '';
  }
}

export function setAnonymousToken(token) {
  const ls = safeLocalStorage();
  if (!ls) return;
  if (typeof token !== 'string' || !token.trim()) return;
  try {
    ls.setItem(STORAGE_KEY, token.trim());
  } catch {
    // Quota / private mode — silently skip
  }
}

export function clearAnonymousToken() {
  const ls = safeLocalStorage();
  if (!ls) return;
  try {
    ls.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

/**
 * Called before a guest cart write: if a token exists it is returned;
 * otherwise a new token is fetched from the backend and stored.
 *
 * Main use-case: creating an identity before adding an item to a guest cart,
 * in the future where AuthGate has been relaxed (or outside the Telegram SDK).
 *
 * Returns: token string (empty string — could not be obtained in any case).
 */
let inFlightFetch = null;
export async function ensureAnonymousToken() {
  const existing = getAnonymousToken();
  if (existing) return existing;

  // Let concurrent callers share a single fetch
  if (inFlightFetch) return inFlightFetch;

  inFlightFetch = (async () => {
    try {
      const res = await fetch('/api/backend/api/v1/cart/anonymous-token', {
        method: 'POST',
        credentials: 'include',
        headers: { accept: 'application/json' },
      });
      if (!res.ok) return '';
      const data = await res.json().catch(() => null);
      const token = typeof data?.token === 'string' ? data.token : '';
      if (token) setAnonymousToken(token);
      return token;
    } catch {
      return '';
    } finally {
      // Clear after a tick so concurrent callers benefit from caching
      setTimeout(() => {
        inFlightFetch = null;
      }, 0);
    }
  })();

  return inFlightFetch;
}
