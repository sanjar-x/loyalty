import { apiClient } from '@/shared/api/clientFetch';

/**
 * Fetch a live SKU pricing preview.
 *
 * Backend uses the same evaluator + resolver as the autonomous recompute, so
 * the returned `finalPrice` matches what `sku.sellingPrice` will land after a
 * save + recompute round-trip. Per CAT-022, productId is optional — when
 * omitted, the backend evaluates the formula against the supplied category +
 * context + supplier inputs alone, which is what we want during create-flow
 * before the product row exists.
 *
 * Body wire shape matches the canonical `MoneySchema`. The form holds
 * `amount` in user-facing units (rubles, yuans, …); we convert to the
 * backend's smallest currency unit (×100) here, mirroring the conversion
 * applied at submit time elsewhere in the form.
 */
export function previewSkuPricing({
  productId = null,
  categoryId,
  contextId,
  purchasePrice,
  supplierId,
  signal,
}) {
  return apiClient.post(
    '/api/pricing/preview-sku',
    {
      // Send productId only when present — keeps the create-flow request
      // shape minimal and avoids tripping any future stricter validators
      // that might gate on key presence.
      ...(productId ? { productId } : {}),
      categoryId,
      contextId,
      purchasePrice: {
        amount: Number(purchasePrice.amount) * 100,
        currency: purchasePrice.currency,
      },
      ...(supplierId ? { supplierId } : {}),
    },
    { signal },
  );
}
