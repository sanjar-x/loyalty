/**
 * Money — kopecks-first qiymat tipini joriy qiluvchi yordamchi modul.
 *
 * Backend `MoneyResponse` ham, `MoneySchema` ham `amount` ni eng kichik
 * birlikda (RUB uchun kopecks, ya'ni 1 RUB = 100) butun son ko'rinishida
 * beradi. UI float'da hisoblamasin — `0.1 + 0.2 = 0.30000000000000004` xatosi
 * va yaxlitlash drift'i. Pul arifmetikasi har doim integer kopecks'da.
 *
 * Ushbu modul mavjud `priceRub` interfeysiga **qo'shimcha**, BC-break yo'q —
 * yangi kod undan foydalanadi, eski call site'lar bosqichma-bosqich
 * ko'chiriladi.
 *
 * @typedef {Object} Money
 * @property {number} amount   eng kichik birlik (RUB → kopecks)
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
 * Backend MoneyResponse / MoneySchema → Money. Nullsafe — null/undefined
 * uchun `zeroMoney(fallbackCurrency)` qaytaradi (UI hech qachon NaN
 * ko'rmasin).
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
  // Yaxlitlash: HALF_EVEN (banker rounding) eng adolatli, lekin
  // `Math.round` yetarli — pul integer'da, faqat factor'da kasr bo'ladi.
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
 * UI-darajasidagi format. Faqat displayda chaqiriladi — hisob-kitobda emas.
 *
 *   format(fromKopecks(150000)) // → "1 500 ₽"
 *
 * Default fraction digits: 0 (RUB uchun standart). Agar foydalanuvchi 0.50 RUB
 * ko'rishni xohlasa `{ minimumFractionDigits: 2 }` kelishilganda override.
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
    // Notanish currency code yoki Intl mavjud emas — sodda fallback
    return `${value.toLocaleString(locale)} ${money.currency}`;
  }
}

/**
 * Legacy interfeys uchun ko'prik. Eski kod `priceRub: number` bilan ishlaydi;
 * yangi adapter'lar Money'ni qaytaradi va eski ichki transformerlar bu helper
 * orqali rubl/float'ga ag'darilishi mumkin (faqat DISPLAY uchun).
 */
export function toRubFloat(money) {
  return money.amount / 100;
}

/**
 * Eski shape'ni Money'ga ko'tarish (migratsiya uchun). `priceRub` numberini
 * kopecks'ga aylantiradi. Aniqlik yo'qotishi mumkin (float→int) — shu tarafsiz
 * faqat migratsiya muddatida ishlatish tavsiya etiladi.
 */
export function fromRubFloat(rubFloat, currency = DEFAULT_CURRENCY) {
  const n = Number(rubFloat);
  if (!Number.isFinite(n)) return zeroMoney(currency);
  return Object.freeze({ amount: Math.round(n * 100), currency });
}

/* ── Public-facing aliaslar (CHK-007) ─────────────────────────────────────
 * `fromKopecks` va `format` nomlari modul ichidagi konvensiyaga mos, lekin
 * yangi UI/totals kodi qisqaroq `money(...)` va `formatMoney(...)` shakliga
 * o'rganib qolgan. Aliaslar BC saqlaydi va mavjud importerlarga ta'sir
 * qilmaydi.
 */
export const money = fromKopecks;
export const formatMoney = format;
