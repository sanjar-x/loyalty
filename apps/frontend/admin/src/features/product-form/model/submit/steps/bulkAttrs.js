import { ensureNotAborted, setStep, SubmitError } from '../state.js';

/**
 * Step 2 — POST /attributes/bulk for product-level attribute assignments.
 * Skipped silently when the form has no product attrs.
 */
export async function bulkAttrs(ctx) {
  if (!ctx.form.bulkAttrsPayload) return;
  ensureNotAborted(ctx);
  setStep(ctx, 'attrs');
  try {
    await ctx.api.bulkAssignAttrs(ctx.productId, ctx.form.bulkAttrsPayload);
  } catch (err) {
    throw new SubmitError({
      step: 'attrs',
      code: err?.code ?? 'BULK_ATTRS_FAILED',
      message: err?.message ?? 'Не удалось назначить атрибуты',
      recoverable: true,
      cause: err,
    });
  }
}
