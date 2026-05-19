import {
  ensureNotAborted,
  setStep,
  SubmitError,
  TRANSIENT_PASS_THROUGH_CODES,
} from '../state.js';

/**
 * Per-variant Step — optional size-guide image with `role: 'size_guide'`.
 *
 * Mirrors the upload chain in uploadMedia but for a single asset. Aborts
 * and rate-limits / transport failures pass through unchanged so the
 * orchestrator can surface the right top-level error; everything else is
 * reclassified into a SIZE_GUIDE_FAILED domain error so the user sees
 * "Не удалось загрузить размерную сетку. Продукт создан как черновик."
 * instead of a generic upload failure that would shadow a different
 * underlying problem.
 */
export async function uploadSizeGuide(ctx) {
  if (!ctx.currentVariantId) return;
  const variant = ctx.form.state.variants[ctx.variantIndex];
  const sizeGuide = variant?.sizeGuide;
  if (!sizeGuide) return;

  ensureNotAborted(ctx);
  setStep(ctx, 'size_guide');

  try {
    let storageObjectId = null;
    let mediaUrl = null;

    const file =
      sizeGuide.file ||
      (sizeGuide.source === 'url'
        ? await ctx.api.fetchImageAsFile(sizeGuide.url)
        : null);
    if (!file) return;

    const slot = await ctx.api.reserveMediaUpload({
      contentType: file.type || 'image/jpeg',
      filename: file.name,
    });
    await ctx.api.uploadToS3(slot.presignedUrl, file);
    await ctx.api.confirmMedia(slot.storageObjectId);
    const metadata = await ctx.api.subscribeMediaStatus(slot.storageObjectId, {
      signal: ctx.signal,
    });
    storageObjectId = slot.storageObjectId;
    mediaUrl = metadata?.url || ctx.api.extractRawUrl(slot.presignedUrl);

    if (!storageObjectId) return;

    await ctx.api.associateMedia(ctx.productId, {
      storageObjectId,
      url: mediaUrl || undefined,
      variantId: ctx.currentVariantId,
      role: 'size_guide',
      sortOrder: 0,
      mediaType: 'image',
      isExternal: false,
    });
  } catch (err) {
    if (err?.name === 'AbortError' || ctx.signal?.aborted) throw err;
    if (TRANSIENT_PASS_THROUGH_CODES.has(err?.code)) throw err;
    throw new SubmitError({
      step: 'size_guide',
      code: 'SIZE_GUIDE_FAILED',
      message:
        'Не удалось загрузить размерную сетку. Продукт создан как черновик.',
      recoverable: true,
      cause: err,
    });
  }
}
