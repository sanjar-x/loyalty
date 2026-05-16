/**
 * Pure transformer: backend `RateQuoteResponse` (camelCase wire shape) →
 * `useCheckoutStore.quote` ichki shape. Asosiy farq — `deliveryAmount`'ni
 * `MoneySchema` ({amount, currency}) tarkibidan kopecks butun son va
 * currency string'iga ajratish (totals.js integer math kutadi).
 *
 * `null`/notog'ri shape (e.g. mutation rejection o'rniga undefined) — null
 * qaytaramiz; chaqiruvchi `clearQuote` qiladi.
 */
function parseIntegerOrNull(value) {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

export function mapRateQuoteResponseToQuote(resp) {
  if (!resp || typeof resp !== 'object') return null;
  const money = resp.deliveryAmount;
  const amount = parseIntegerOrNull(money?.amount);
  return {
    quoteId: resp.quoteId,
    providerCode: resp.providerCode,
    serviceCode: resp.serviceCode,
    serviceName: resp.serviceName,
    deliveryType: resp.deliveryType,
    deliveryAmount: amount ?? 0,
    currency: (money && typeof money.currency === 'string' && money.currency) || 'RUB',
    deliveryDaysMin: parseIntegerOrNull(resp.deliveryDaysMin),
    deliveryDaysMax: parseIntegerOrNull(resp.deliveryDaysMax),
    quotedAt: resp.quotedAt ?? null,
    expiresAt: resp.expiresAt ?? null,
    fallbackAlternatives: Array.isArray(resp.fallbackAlternatives)
      ? resp.fallbackAlternatives.filter((c) => typeof c === 'string' && c)
      : [],
  };
}
