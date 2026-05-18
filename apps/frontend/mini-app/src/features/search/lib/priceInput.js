/**
 * Pure helpers for caret-aware price input in FiltersSheet/PriceSheet.
 * Sprint 1.3 — extracted here from two identical copies.
 *
 * All functions are pure, no DOM. Tested in isolation.
 */

export const MAX_DIGITS = 6;

export function toDigits(value) {
  const digits = String(value || '').replace(/[^0-9]/g, '');
  return digits.slice(0, MAX_DIGITS);
}

export function digitsToNumber(value) {
  const n = Number(toDigits(value));
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function formatNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '';
  return n.toLocaleString('ru-RU');
}

export function formatNumberFromDigits(digits) {
  const n = Number(digits);
  if (!digits || !Number.isFinite(n)) return '';
  return formatNumber(n);
}

export function buildCurrencyValue(digits) {
  if (!digits) return '';
  return `${formatNumberFromDigits(digits)} ₽`;
}

export function countDigitsBeforeCaret(text, caretPos) {
  return text.slice(0, caretPos).replace(/\D/g, '').length;
}

/**
 * `digitsBeforeCaret` → caret position in the formatted string (accounts for
 * the ₽ suffix so the caret doesn't "fall into" the suffix zone).
 */
export function findCaretPosByDigitIndex(formattedText, digitsBeforeCaret) {
  let pos = 0;
  let seenDigits = 0;

  while (pos < formattedText.length && seenDigits < digitsBeforeCaret) {
    if (/\d/.test(formattedText[pos])) seenDigits++;
    pos++;
  }

  const rubIndex = formattedText.indexOf('₽');
  if (rubIndex !== -1 && pos > rubIndex - 1) {
    pos = rubIndex - 1;
  }

  return pos;
}
