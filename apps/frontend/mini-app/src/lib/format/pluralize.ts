/**
 * Proper Russian pluralization following grammar rules.
 * Handles all number forms including 11-19, 21, 101, etc.
 *
 * @param count - The number to pluralize for
 * @param one - Form for 1, 21, 31... (e.g., "товар", "отзыв")
 * @param few - Form for 2-4, 22-24... (e.g., "товара", "отзыва")
 * @param many - Form for 0, 5-20, 25-30... (e.g., "товаров", "отзывов")
 *
 * @example pluralizeRu(1, "товар", "товара", "товаров") => "товар"
 * @example pluralizeRu(21, "товар", "товара", "товаров") => "товар"
 * @example pluralizeRu(5, "товар", "товара", "товаров") => "товаров"
 */
export function pluralizeRu(
  count: number,
  one: string,
  few: string,
  many: string,
): string {
  const abs = Math.abs(count);
  const mod10 = abs % 10;
  const mod100 = abs % 100;

  if (mod100 >= 11 && mod100 <= 19) return many;
  if (mod10 === 1) return one;
  if (mod10 >= 2 && mod10 <= 4) return few;
  return many;
}

/**
 * Pluralize with the count included.
 * @example pluralizeWithCount(5, "товар", "товара", "товаров") => "5 товаров"
 */
export function pluralizeWithCount(
  count: number,
  one: string,
  few: string,
  many: string,
): string {
  return `${count} ${pluralizeRu(count, one, few, many)}`;
}
