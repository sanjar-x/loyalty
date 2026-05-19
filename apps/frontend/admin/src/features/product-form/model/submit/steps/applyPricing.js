import { ensureNotAborted, setStep, SubmitError } from '../state.js';

/**
 * Per-variant Step — apply per-SKU price overrides + variant-level
 * purchasePrice patches.
 *
 * Both sub-flows share a single listSkus() call so we don't pay for two
 * round-trips when both apply. Patches are issued in parallel.
 *
 * Skipped when there's nothing to patch (no per-SKU price overrides AND
 * no variant-level purchasePrice).
 */
export async function applyPricing(ctx) {
  if (!ctx.currentVariantId) return;
  const vp = ctx.form.variantPayloads?.[ctx.variantIndex];
  if (!vp?.skuGeneratePayload) return;

  const needsPerSkuPatch = (vp.perSkuPriceUpdates ?? []).length > 0;
  const variantPurchasePrice = vp.variantPurchasePrice ?? null;
  if (!needsPerSkuPatch && !variantPurchasePrice) return;

  ensureNotAborted(ctx);
  setStep(ctx, 'pricing');

  let skus;
  try {
    const skuList = await ctx.api.listSkus(ctx.productId, ctx.currentVariantId);
    skus = skuList.items ?? [];
  } catch (err) {
    throw new SubmitError({
      step: 'pricing',
      code: err?.code ?? 'LIST_SKUS_FAILED',
      message: err?.message ?? 'Не удалось получить список SKU',
      recoverable: true,
      cause: err,
    });
  }

  const patches = [];
  if (needsPerSkuPatch) {
    for (const priceUpdate of vp.perSkuPriceUpdates) {
      const sku = skus.find((s) =>
        (s.variantAttributes ?? []).some(
          (va) => va.attributeValueId === priceUpdate.valueId,
        ),
      );
      if (!sku) continue;
      patches.push(
        ctx.api.updateSku(ctx.productId, ctx.currentVariantId, sku.id, {
          price: priceUpdate.price,
          compareAtPrice: priceUpdate.compareAtPrice,
          // CAT-002: variant-level purchasePrice applies to all SKUs of
          // the variant. Folded into the same PATCH so we issue one
          // round-trip per SKU instead of two.
          ...(variantPurchasePrice
            ? { purchasePrice: variantPurchasePrice }
            : {}),
        }),
      );
    }
  } else if (variantPurchasePrice) {
    // Flat pricing — purchasePrice still needs to land on each generated
    // SKU so the recompute pipeline (ADR-005) has its input.
    for (const sku of skus) {
      patches.push(
        ctx.api.updateSku(ctx.productId, ctx.currentVariantId, sku.id, {
          purchasePrice: variantPurchasePrice,
        }),
      );
    }
  }

  try {
    await Promise.all(patches);
  } catch (err) {
    throw new SubmitError({
      step: 'pricing',
      code: err?.code ?? 'APPLY_PRICING_FAILED',
      message: err?.message ?? 'Не удалось применить цены',
      recoverable: true,
      cause: err,
    });
  }
}
