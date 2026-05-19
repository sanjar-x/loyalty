/**
 * Idempotency key for POST /api/v1/orders/buy-now.
 *
 * Backend `BuyNowOrderRequest.idempotencyKey` validates 8..128 chars
 * (Pydantic). Format `buy-now-YYYYMMDD-<nanoid8>` — easy to grep in
 * logs / Sentry / outbox table, stable length ~25 chars.
 *
 * Single key per buy-now attempt: regenerated only after a confirmed
 * success or full reset. Network retry of `/orders/buy-now` re-uses the
 * key so the backend dedup returns the same `order_id` instead of
 * creating a duplicate (`IIdempotencyStore` scope `order.create_buy_now`,
 * TTL 24h — see audit §1.1).
 */

const ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz';
const NANO_LENGTH = 8;

function todayCompact() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}${mm}${dd}`;
}

function randomNano(length = NANO_LENGTH) {
  // `crypto.getRandomValues` — uniformly distributed; falls back to
  // Math.random in jsdom test envs without Web Crypto (collision risk is
  // negligible at 36^8 ≈ 2.8e12 per day).
  const bytes = new Uint8Array(length);
  try {
    if (typeof globalThis.crypto?.getRandomValues === 'function') {
      globalThis.crypto.getRandomValues(bytes);
    } else {
      for (let i = 0; i < length; i++) bytes[i] = Math.floor(Math.random() * 256);
    }
  } catch {
    for (let i = 0; i < length; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  let out = '';
  for (let i = 0; i < length; i++) {
    out += ALPHABET[bytes[i] % ALPHABET.length];
  }
  return out;
}

export function generateBuyNowIdempotencyKey() {
  return `buy-now-${todayCompact()}-${randomNano()}`;
}
