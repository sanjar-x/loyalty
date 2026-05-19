import { ensureNotAborted, setStep, SubmitError } from '../state.js';

/**
 * Per-variant Step — POST /variants/{vid}/skus/generate.
 *
 * Skipped when the variant has no `skuGeneratePayload` (no variant attrs)
 * or when the variant itself was skipped by createVariants (empty variant).
 *
 * Backend may return `createdCount === 0 && skippedCount === 0` if the
 * matrix collapses to nothing — that's a user-facing problem (form lets
 * the user submit without selecting variant attribute values), so we
 * surface it as an unrecoverable ZERO_SKUS error.
 */
export async function generateSkus(ctx) {
  if (!ctx.currentVariantId) return;
  const vp = ctx.form.variantPayloads?.[ctx.variantIndex];
  if (!vp?.skuGeneratePayload) return;

  ensureNotAborted(ctx);
  const variants = ctx.form.state.variants;
  const message =
    variants.length > 1
      ? `Генерация SKU... (вариант ${ctx.variantIndex + 1}/${variants.length})`
      : undefined;
  setStep(ctx, 'skus', message);

  let result;
  try {
    result = await ctx.api.generateSkus(
      ctx.productId,
      ctx.currentVariantId,
      vp.skuGeneratePayload,
    );
  } catch (err) {
    throw new SubmitError({
      step: 'skus',
      code: err?.code ?? 'GENERATE_SKUS_FAILED',
      message: err?.message ?? 'Не удалось сгенерировать SKU',
      recoverable: true,
      cause: err,
    });
  }

  if ((result?.createdCount ?? 0) === 0 && (result?.skippedCount ?? 0) === 0) {
    throw new SubmitError({
      step: 'skus',
      code: 'ZERO_SKUS',
      message: 'SKU не были сгенерированы. Проверьте выбранные атрибуты.',
      recoverable: true,
    });
  }
}
