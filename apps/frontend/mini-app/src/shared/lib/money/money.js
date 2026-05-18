/**
 * Money — helper module that introduces a kopecks-first value type.
 *
 * Both backend `MoneyResponse` and `MoneySchema` provide `amount` as an integer
 * in the smallest unit (kopecks for RUB, i.e. 1 RUB = 100). UI must not compute
 * in floats — the `0.1 + 0.2 = 0.30000000000000004` error and rounding drift.
 * Money arithmetic is always done in integer kopecks.
 *
 * This module is **additive** to the existing `priceRub` interface, with no
 * BC break — new code uses it, and old call sites are migrated incrementally.
 *
 * @typedef {Object} Money
 * @property {number} amount   smallest unit (RUB → kopecks)
 * @property {string} currency ISO 4217 (RUB, USD, ...)
 */

const DEFAULT_CURRENCY = 'RUB';

function assertInt(n, label = 'amount') {
  if (!Number.isFinite(n)) {
    throw new TypeError(`Money.${label} must be a finite number, got ${n}`);
  }
  if (!Number.isInteger(n)) {
    throw new TypeError(`Money.${label} must be an integer (kopecks), got ${n}`);
  }
}

function assertSameCurrency(a, b) {
  if (a.currency !== b.currency) {
    throw new TypeError(`Money currency mismatch: ${a.currency} vs ${b.currency}`);
  }
}

export function zeroMoney(currency = DEFAULT_CURRENCY) {
  return Object.freeze({ amount: 0, currency });
}

export function fromKopecks(kopecks, currency = DEFAULT_CURRENCY) {
  const n = Number(kopecks);
  assertInt(n, 'amount');
  return Object.freeze({ amount: n, currency });
}

/**
 * Backend MoneyResponse / MoneySchema → Money. Nullsafe — returns
 * `zeroMoney(fallbackCurrency)` for null/undefined (UI must never see NaN).
 */
export function fromMoneyResponse(money, fallbackCurrency = DEFAULT_CURRENCY) {
  if (money == null) return zeroMoney(fallbackCurrency);
  const amount = Number(money.amount);
  if (!Number.isFinite(amount)) return zeroMoney(money.currency || fallbackCurrency);
  return Object.freeze({
    amount: Math.trunc(amount),
    currency: money.currency || fallbackCurrency,
  });
}

export function add(a, b) {
  assertSameCurrency(a, b);
  return Object.freeze({ amount: a.amount + b.amount, currency: a.currency });
}

export function subtract(a, b) {
  assertSameCurrency(a, b);
  return Object.freeze({ amount: a.amount - b.amount, currency: a.currency });
}

export function multiply(money, factor) {
  const n = Number(factor);
  if (!Number.isFinite(n)) {
    throw new TypeError(`Money.multiply factor must be finite, got ${factor}`);
  }
  // Rounding: HALF_EVEN (banker's rounding) is the fairest, but
  // `Math.round` is enough — money is an integer, only the factor can be fractional.
  return Object.freeze({
    amount: Math.round(money.amount * n),
    currency: money.currency,
  });
}

export function isZero(money) {
  return money.amount === 0;
}

export function isPositive(money) {
  return money.amount > 0;
}

export function compare(a, b) {
  assertSameCurrency(a, b);
  return a.amount - b.amount;
}

/**
 * UI-level format. Called only on display — not in calculations.
 *
 *   format(fromKopecks(150000)) // → "1 500 ₽"
 *
 * Default fraction digits: 0 (standard for RUB). If the user wants to see 0.50 RUB,
 * override with `{ minimumFractionDigits: 2 }` by agreement.
 */
export function format(money, options = {}) {
  const { locale = 'ru-RU', minimumFractionDigits = 0, maximumFractionDigits = 0 } = options;
  const value = money.amount / 100;
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: money.currency,
      minimumFractionDigits,
      maximumFractionDigits,
    }).format(value);
  } catch {
    // Unknown currency code or Intl not available — simple fallback
    return `${value.toLocaleString(locale)} ${money.currency}`;
  }
}

/**
 * Bridge for the legacy interface. Old code works with `priceRub: number`;
 * new adapters return Money, and old internal transformers can convert it to
 * a ruble/float via this helper (DISPLAY only).
 */
export function toRubFloat(money) {
  return money.amount / 100;
}

/**
 * Lift the old shape into Money (for migration). Converts a `priceRub` number
 * into kopecks. May lose precision (float→int) — for this reason it is
 * recommended only during the migration period.
 */
export function fromRubFloat(rubFloat, currency = DEFAULT_CURRENCY) {
  const n = Number(rubFloat);
  if (!Number.isFinite(n)) return zeroMoney(currency);
  return Object.freeze({ amount: Math.round(n * 100), currency });
}

/* ── Public-facing aliases (CHK-007) ─────────────────────────────────────
 * The names `fromKopecks` and `format` follow the module-internal convention,
 * but new UI/totals code is used to the shorter `money(...)` and `formatMoney(...)`
 * shapes. The aliases preserve BC and do not affect existing importers.
 */
export const money = fromKopecks;
export const formatMoney = format;
