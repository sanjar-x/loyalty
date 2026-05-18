/**
 * Bank card helpers — generic plumbing (formatting + Luhn). Sprint 2:
 * moved out of shared/lib/validators. Business logic (validateCardDraft
 * with fields draft/holder/exp/cvc) lives in
 * features/checkout-flow/lib/validators.
 */

export function normalizeCardNumberDigits(input) {
  return (input || '').replace(/\D/g, '').slice(0, 19);
}

export function formatCardNumber(digits) {
  const d = (digits || '').replace(/\D/g, '');
  return d.replace(/(.{4})/g, '$1 ').trim();
}

export function normalizeExpiry(value) {
  const digits = (value || '').replace(/\D/g, '').slice(0, 4);
  const mm = digits.slice(0, 2);
  const yy = digits.slice(2, 4);
  return yy ? `${mm}/${yy}` : mm;
}

export function isValidLuhn(numberDigits) {
  const digits = (numberDigits || '').replace(/\D/g, '');
  if (digits.length < 12) return false;
  let sum = 0;
  let shouldDouble = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = Number(digits[i]);
    if (Number.isNaN(digit)) return false;
    if (shouldDouble) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    shouldDouble = !shouldDouble;
  }
  return sum % 10 === 0;
}
