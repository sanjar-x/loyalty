/**
 * Format a number as Russian ruble price with thousands separator.
 * @example formatRub(12500) => "12 500 ₽"
 */
export function formatRub(value: number | string | null | undefined): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  const rounded = Math.trunc(n);
  const formatted = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${formatted} ₽`;
}

/**
 * Compact ruble format without the currency symbol.
 * @example formatRubCompact(12500) => "12 500"
 */
export function formatRubCompact(value: number | string | null | undefined): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  const rounded = Math.trunc(n);
  return rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/**
 * Calculate monthly split payment amount.
 * @example formatSplitPayment(12000, 4) => "3000"
 */
export function formatSplitPayment(
  totalPrice: number,
  installments: number = 4,
): string {
  if (!Number.isFinite(totalPrice) || totalPrice <= 0) return "0";
  return String(Math.ceil(totalPrice / installments));
}
