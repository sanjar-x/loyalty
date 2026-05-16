/**
 * Customer-facing feature flags — backend hali ship qilmagan funksiyalar
 * uchun explicit gate (`Spec §11`). Default — hammasi `false`.
 *
 * Konvensiya: `NEXT_PUBLIC_FEATURE_<NAME>=true` enable qiladi. Literal `'true'`
 * bilan solishtiramiz — `'false'` truthy bo'lib qolmasligi uchun (`Boolean('false') === true`).
 *
 * Backend endpoint ship qilganda: `lib/store/api/hooks.js`'da tegishli
 * `pendingFeatureQuery` stub'ni `FEATURES.<FLAG> ? realRtkHook : stub`
 * pattern bilan almashtiring.
 *
 * Audit #8: `notImplemented*` xom stub'lar shu yerdagi nomli bayroqlarga
 * bog'landi — har feature uchun aniq env var + kanonik flip-paytdagi
 * upgrade payi.
 */
const isOn = (name) =>
  String(process.env[name] || '')
    .toLowerCase()
    .trim() === 'true';

export const FEATURES = Object.freeze({
  /** Referrals — `/api/v1/referrals/*` (пригласи друга, статистика). */
  REFERRALS: isOn('NEXT_PUBLIC_FEATURE_REFERRALS'),
  /** Loyalty points — `/api/v1/points/*` (баллы, история, списание). */
  LOYALTY_POINTS: isOn('NEXT_PUBLIC_FEATURE_LOYALTY_POINTS'),
  /** Categories-with-types meta — `/api/v1/storefront/categories/with-types`. */
  CATEGORIES_WITH_TYPES: isOn('NEXT_PUBLIC_FEATURE_CATEGORIES_WITH_TYPES'),
  /** Order status stream / poll — отдельный endpoint вне `/orders/{id}`. */
  ORDER_STATUS_STREAM: isOn('NEXT_PUBLIC_FEATURE_ORDER_STATUS_STREAM'),
});
