import { buildI18nPayload } from '@/shared/lib/utils';
import { ensureNotAborted, setStep, SubmitError } from '../state.js';

/**
 * Per-variant Step — resolves the variant id used by the rest of the
 * per-variant pipeline.
 *
 * - `vi === 0` → reuse `defaultVariantId` from createProduct (backend
 *   provisions one as part of the product create).
 * - `vi > 0`  → POST /variants. Empty additional variants (no attrs,
 *   no images, no price input) are skipped: the orchestrator will
 *   detect `currentVariantId === null` and skip the rest of the
 *   per-variant pipeline for that index.
 */
function isVariantEmpty(variant) {
  const noAttrs = !Object.values(variant.variantAttrs ?? {}).some(
    (ids) => ids.length > 0,
  );
  const noImages = (variant.images ?? []).length === 0;
  const noPrice = !variant.price?.amount && !variant.purchasePrice?.amount;
  return noAttrs && noImages && noPrice;
}

export async function createVariants(ctx) {
  const variants = ctx.form.state.variants;
  const vi = ctx.variantIndex;
  const variant = variants[vi];

  if (!variant) {
    ctx.currentVariantId = null;
    return;
  }

  if (vi === 0) {
    ctx.currentVariantId = ctx.defaultVariantId;
    return;
  }

  if (isVariantEmpty(variant)) {
    ctx.currentVariantId = null;
    return;
  }

  ensureNotAborted(ctx);
  setStep(
    ctx,
    'variants',
    `Создание вариантов... (${vi + 1}/${variants.length})`,
  );

  try {
    const created = await ctx.api.createVariant(ctx.productId, {
      nameI18N: buildI18nPayload(`Вариант ${vi + 1}`),
      sortOrder: vi,
    });
    ctx.currentVariantId = created.id;
  } catch (err) {
    throw new SubmitError({
      step: 'variants',
      code: err?.code ?? 'CREATE_VARIANT_FAILED',
      message: err?.message ?? 'Не удалось создать вариант',
      recoverable: true,
      cause: err,
    });
  }
}
