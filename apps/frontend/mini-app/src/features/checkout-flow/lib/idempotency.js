/**
 * Idempotency primitive (CHK-006).
 *
 * Protection against pay-button double-tap is two-layered:
 *  1. **Inflight guard** — a second simultaneous `placeOrder()` call is
 *     silently rejected (UI keeps the waiting state).
 *  2. **Idempotency-Key header** — if a network retry happens (502, timeout),
 *     the same header is sent → backend doesn't create a duplicate order.
 *     Defensive until the backend supports it: the header is silently round-tripped.
 *
 * This module is React-free, pure — `useCheckoutFlow` instantiates it via
 * `useRef` and manages the lifecycle. The state machine is simple:
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
 * Fallback when `crypto.randomUUID` is unavailable (jsdom test env sometimes
 * older Node). Our usage requires only a UUID-shaped key, no collision risk
 * (per-attempt, lifetime in seconds).
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
 * Lives inside `useCheckoutFlow` via `useRef`s:
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
 * Simplifies the API via ref management — the pure functions mutate the
 * ref, and the ref is React's standard no-re-render mechanism. In tests we
 * simulate it with a plain `{ current: ... }` object.
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
