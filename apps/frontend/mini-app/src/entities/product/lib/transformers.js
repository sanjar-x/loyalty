/**
 * Pure transformResponse helpers — so that both `enhanceEndpoints`
 * in `lib/store/api.js` and unit tests can call the same function.
 *
 * No RTKQ/Redux imports here — functions are pure, input/output-only.
 */

import { mapStorefrontProduct } from './mapStorefrontProduct';

/**
 * Transforms the `GET /api/v1/storefront/for-you` response into the UI shape.
 *
 * The backend returns meta fields in snake_case for this endpoint
 * (`next_cursor`, `strategy_version`, `is_personalized`), while other
 * storefront listings use camelCase. A tolerant adapter — it accepts both
 * conventions and will not break if the backend unifies them in the future.
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
