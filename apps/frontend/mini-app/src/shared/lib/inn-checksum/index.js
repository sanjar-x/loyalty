/**
 * Russian individual taxpayer number (ИНН) checksum validator.
 *
 * Minfin / FNS spec: a 12-digit individual ИНН (физлицо) has two control
 * digits (positions 11 and 12, 1-indexed) computed via mod-11-twice over
 * the preceding digits. The Passport bounded context (ADR-011) stores
 * `inn` as a customs document field; the backend validates the checksum
 * server-side, but surfacing it client-side prevents a wasted POST and
 * a confusing 422 response.
 *
 * 10-digit ИНН (юрлицо) is a separate format; this app only handles
 * физлицо, so the 10-digit case is rejected for clarity.
 *
 * Algorithm:
 *   coef11 = [7,  2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
 *   coef12 = [3,  7, 2,  4, 10, 3, 5, 9, 4, 6, 8, 0]
 *
 *   d11 = (sum_{i=0..10} digit[i] * coef11[i]) % 11 % 10
 *   d12 = (sum_{i=0..11} digit[i] * coef12[i]) % 11 % 10
 *
 *   valid ⇔ digit[10] == d11 ∧ digit[11] == d12
 */

const COEFFICIENTS_11 = Object.freeze([7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]);
const COEFFICIENTS_12 = Object.freeze([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]);

function digitArray(value) {
  if (typeof value !== 'string') return null;
  const digits = value.replace(/\D/g, '');
  if (digits.length !== 12) return null;
  const arr = new Array(12);
  for (let i = 0; i < 12; i++) {
    arr[i] = digits.charCodeAt(i) - 48;
  }
  return arr;
}

function controlDigit(digits, coefficients) {
  let sum = 0;
  for (let i = 0; i < coefficients.length; i++) {
    sum += digits[i] * coefficients[i];
  }
  return (sum % 11) % 10;
}

/**
 * @param {string} value — raw user input (digits and separators OK)
 * @returns {boolean} — true iff the 12-digit ИНН has valid mod-11-twice
 *                     checksums; false on length / format mismatch or
 *                     digit mismatch.
 */
export function isValidInn(value) {
  const digits = digitArray(value);
  if (!digits) return false;
  const d11 = controlDigit(digits, COEFFICIENTS_11);
  if (digits[10] !== d11) return false;
  const d12 = controlDigit(digits, COEFFICIENTS_12);
  return digits[11] === d12;
}
