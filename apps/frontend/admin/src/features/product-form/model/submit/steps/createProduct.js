import { ensureNotAborted, setStep, SubmitError } from '../state.js';

/**
 * Step 1 — POST /api/catalog/products with the productPayload.
 *
 * On success: stores `productId` and `defaultVariantId` on the context and
 * fires `onProductCreated` so the consumer can light up the "продукт уже
 * сохранён" banner if a later step fails.
 */
export async function createProduct(ctx) {
  ensureNotAborted(ctx);
  setStep(ctx, 'creating');
  try {
    const result = await ctx.api.createProduct(ctx.form.productPayload);
    ctx.productId = result.id;
    ctx.defaultVariantId = result.defaultVariantId;
    ctx.onProductCreated(result.id);
  } catch (err) {
    throw new SubmitError({
      step: 'creating',
      code: err?.code ?? 'CREATE_PRODUCT_FAILED',
      message: err?.message ?? 'Не удалось создать продукт',
      cause: err,
    });
  }
}
