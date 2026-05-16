/**
 * Idempotency primitive (CHK-006).
 *
 * Pay-button double-tap'ga qarshi himoya ikki qatlamli:
 *  1. **Inflight guard** — bir vaqtning o'zida ikkinchi `placeOrder()`
 *     chaqiruvi silent ravishda rad etiladi (UI'da kutib turibmiz).
 *  2. **Idempotency-Key header** — agar tarmoq retry bo'lsa (502, timeout),
 *     bir xil header bilan jo'natiladi → backend duplikat order yaratmaydi.
 *     Backend qabul qilguncha defensive: header silently borib qaytadi.
 *
 * Bu modul React'siz, pure — `useCheckoutFlow` `useRef` orqali instansiyalaydi
 * va lifecycle'ni boshqaradi. State machine sodda:
 *
 *   idle  ──acquire──▶  inflight
 *     ▲                   │
 *     │                   ├──success──▶  reset key  ──▶  idle
 *     │                   └──fail─────▶  keep key   ──▶  idle (retry uses same key)
 *
 * @typedef {Object} IdempotencyState
 * @property {boolean} inflight
 * @property {string | null} key
 */

/**
 * `crypto.randomUUID` mavjud bo'lmaganda fallback (jsdom test env ba'zan
 * eski Node). Bizning ishlatish maqsadi — UUID-shape kalit, kollizion xavf
 * yo'q (per-attempt, lifetime soniyalar).
 */
function safeUUID() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  const hex = (n) =>
    Math.floor(Math.random() * 16 ** n)
      .toString(16)
      .padStart(n, '0');
  return `${hex(8)}-${hex(4)}-${hex(4)}-${hex(4)}-${hex(12)}`;
}

/**
 * `useCheckoutFlow`'da `useRef`'lar orqali yashaydi:
 *
 * ```js
 * const inflightRef = useRef(false);
 * const keyRef = useRef(null);
 *
 * if (!acquireInflight(inflightRef)) return null;     // busy
 * const key = ensureKey(keyRef);
 * try {
 *   // ... initiate({ ..., __idempotencyKey: key }) ...
 *   resetKey(keyRef);   // success: clear so next attempt has fresh key
 * } finally {
 *   releaseInflight(inflightRef);
 * }
 * ```
 *
 * Ref boshqaruvi bilan API'ni soddalashtirgan — pure funksiyalar refni
 * mutate qiladi, lekin ref o'zi React'ning standart re-render'siz ko'pchilik
 * xilma-xil mexanizmi. Test'da `{ current: ... }` plain object bilan
 * simulyatsiya qilamiz.
 */
export function acquireInflight(ref) {
  if (!ref || typeof ref !== 'object') return false;
  if (ref.current === true) return false;
  ref.current = true;
  return true;
}

export function releaseInflight(ref) {
  if (!ref || typeof ref !== 'object') return;
  ref.current = false;
}

export function ensureKey(ref, generator = safeUUID) {
  if (!ref || typeof ref !== 'object') return null;
  if (typeof ref.current === 'string' && ref.current.length > 0) {
    return ref.current;
  }
  const key = generator();
  ref.current = key;
  return key;
}

export function resetKey(ref) {
  if (!ref || typeof ref !== 'object') return;
  ref.current = null;
}

export { safeUUID };
