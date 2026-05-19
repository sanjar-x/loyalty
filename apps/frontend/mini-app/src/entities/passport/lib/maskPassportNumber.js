/**
 * Mask a 4+6 ИРФ passport identifier for list views (PII minimisation).
 *
 *   maskPassportNumber('1234567890') → '1234 5****0'
 *   maskPassportNumber('1234', '567890') → '1234 5****0'
 *
 * Format: first 4 digits (series) unchanged + space + first and last
 * digit of the 6-digit number visible, middle 4 digits replaced with
 * asterisks. Anything that doesn't match the expected length collapses
 * to the original input (graceful degradation — caller may want to
 * surface "Паспорт неполный" UI on its own).
 */
function digitsOnly(value) {
  return typeof value === 'string' ? value.replace(/\D/g, '') : '';
}

export function maskPassportNumber(serialOrFull, maybeNumber) {
  const serialDigits = digitsOnly(serialOrFull);
  const numberDigits = maybeNumber == null ? serialDigits.slice(4) : digitsOnly(maybeNumber);
  const series = serialDigits.slice(0, 4);

  if (series.length !== 4 || numberDigits.length !== 6) {
    // Pass through whatever the caller gave us; the consumer can decide
    // how to render an incomplete passport.
    const fallback = `${serialDigits}${maybeNumber == null ? '' : digitsOnly(maybeNumber)}`;
    return fallback || (typeof serialOrFull === 'string' ? serialOrFull : '');
  }

  const first = numberDigits[0];
  const last = numberDigits[5];
  return `${series} ${first}****${last}`;
}
