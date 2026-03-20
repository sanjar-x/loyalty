export function formatRubPrice(value: number | string | null | undefined): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  const rounded = Math.trunc(n);
  const formatted = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${formatted} ₽`;
}

export function formatSplitPayment(
  totalPrice: number,
  installments: number = 4,
): string {
  if (!Number.isFinite(totalPrice) || totalPrice <= 0) return "0";
  return String(Math.ceil(totalPrice / installments));
}
