/**
 * Pure transformResponse helperlari — `lib/store/api.js`'dagi
 * `enhanceEndpoints` ichida ham, unit test'larda ham bir xil
 * funksiyani chaqirish uchun.
 *
 * Bu yerda hech qanday RTKQ/Redux import yo'q — funksiyalar pure,
 * input/output-only.
 */

import { mapStorefrontProduct } from '@/lib/adapters/mapStorefrontProduct';

/**
 * `GET /api/v1/storefront/for-you` javobini UI shape'iga ag'daradi.
 *
 * Backend bu endpointda meta-maydonlarni snake_case'da qaytaradi
 * (`next_cursor`, `strategy_version`, `is_personalized`), boshqa
 * storefront ro'yxatlari esa camelCase'da. Tolerant adapter — ikkala
 * konvensiyani ham qabul qiladi, kelajakda backend birlashtirsa
 * ham buzilmaydi.
 */
export function transformForYouFeed(response) {
  const items = Array.isArray(response?.items) ? response.items : [];
  const nextCursor = response?.nextCursor ?? response?.next_cursor ?? null;
  const strategyVersion = response?.strategyVersion ?? response?.strategy_version ?? null;
  const isPersonalized = response?.isPersonalized ?? response?.is_personalized ?? false;

  return {
    items: items.map(mapStorefrontProduct).filter(Boolean),
    nextCursor,
    hasNext: Boolean(nextCursor),
    strategyVersion,
    isPersonalized: Boolean(isPersonalized),
  };
}
