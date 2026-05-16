/**
 * Anonymous cart token storage.
 *
 * Spec: SPEC - Frontend Integration Guide §7
 *   - Mehmon (guest) korzinka ID'si `X-Anonymous-Token` header orqali
 *     yuboriladi. Token'ni backend `POST /api/v1/cart/anonymous-token`
 *     beradi.
 *   - Login'dan keyin `POST /api/v1/cart/merge {anonymousToken}` chaqiriladi
 *     va shu paytda token o'chiriladi (qayta merge'ni oldini olish uchun).
 *
 * Storage: localStorage. SSR-safe (`window` mavjud emasligini tekshiradi).
 * Garchi backend tokenni bir necha hafta saqlasa ham, frontend uchun
 * "merge yoki tashlab ket" — ikki holatdan biri bo'lishi kifoya.
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
 * Guest cart write'idan oldin chaqiriladi: token mavjud bo'lsa qaytaradi,
 * yo'q bo'lsa backend'dan yangi token oladi va saqlaydi.
 *
 * Asosiy use-case: AuthGate yumshatilgan kelajakda (yoki Telegram SDK
 * tashqarisida) guest savatga element qo'shishdan oldin identity yaratish.
 *
 * Returns: token string (bo'sh string — hech qanday holatda olib bo'lmadi).
 */
let inFlightFetch = null;
export async function ensureAnonymousToken() {
  const existing = getAnonymousToken();
  if (existing) return existing;

  // Concurrent caller'lar bitta fetch'ni baham ko'rsin
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
      // Tick'dan keyin tozalaymiz, concurrent caller'lar uchun cache
      setTimeout(() => {
        inFlightFetch = null;
      }, 0);
    }
  })();

  return inFlightFetch;
}
