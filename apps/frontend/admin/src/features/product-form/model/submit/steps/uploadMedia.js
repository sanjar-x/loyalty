import { selectBgRemovedMedia } from '../../useBgRemoval';
import { ensureNotAborted, setStep } from '../state.js';

const CHUNK_SIZE = 3;

/**
 * Per-variant Step — upload images and attach them to the product.
 *
 * Each chunk of 3 images runs in parallel via Promise.allSettled so a
 * single failure doesn't block the rest. Failures are accumulated on
 * `ctx.totalMediaFailures` and surfaced in the orchestrator's final
 * MEDIA_PARTIAL_FAILURE error after every variant has been processed
 * (matching the behaviour the original useSubmitProduct shipped).
 *
 * Pre-uploaded images (status: 'completed' from useImageUpload's eager
 * upload) skip the reserve/upload/confirm/SSE chain — only the
 * associateMedia step runs.
 */
export async function uploadMedia(ctx) {
  if (!ctx.currentVariantId) return;
  const variant = ctx.form.state.variants[ctx.variantIndex];
  const images = variant?.images ?? [];
  if (images.length === 0) return;

  ensureNotAborted(ctx);
  ctx.totalMediaCount += images.length;

  const variants = ctx.form.state.variants;
  const totalLabel =
    variants.length > 1
      ? `Загрузка и обработка изображений (вариант ${ctx.variantIndex + 1})`
      : 'Загрузка и обработка изображений';

  let uploaded = 0;
  setStep(ctx, 'media', `${totalLabel} (${uploaded}/${images.length})...`);

  const tasks = images.map((image, idx) => ({
    image,
    role: idx === 0 ? 'main' : 'gallery',
    sortOrder: idx,
    preUploaded: ctx.imageUploads[image.localId],
  }));

  let failures = 0;
  for (let i = 0; i < tasks.length; i += CHUNK_SIZE) {
    ensureNotAborted(ctx);
    const chunk = tasks.slice(i, i + CHUNK_SIZE);
    const results = await Promise.allSettled(
      chunk.map((task) => uploadOne(ctx, task)),
    );
    for (const r of results) {
      if (r.status === 'fulfilled') uploaded += 1;
      else failures += 1;
    }
    setStep(ctx, 'media', `${totalLabel} (${uploaded}/${images.length})...`);
  }

  ctx.totalMediaFailures += failures;
}

async function uploadOne(ctx, { image, role, sortOrder, preUploaded }) {
  let storageObjectId = null;
  let mediaUrl = null;

  if (preUploaded?.status === 'completed' && preUploaded.storageObjectId) {
    storageObjectId = preUploaded.storageObjectId;
    mediaUrl = preUploaded.url || preUploaded.rawUrl || null;
  } else {
    const file =
      image.file ||
      (image.source === 'url'
        ? await ctx.api.fetchImageAsFile(image.url)
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
  }

  if (!storageObjectId) return;

  // Swap in the derived (no-background) target when the merchandiser
  // applied bg-removal to this image. Mirrors the resolution rule used
  // by the gallery thumbnail / preview card so backend stores the same
  // asset that was shown in the editor — without this, the save would
  // silently ship the original even though the UI confirmed the cutout.
  const bgTarget = selectBgRemovedMedia(ctx.bgRemoval, image.localId);
  if (bgTarget) {
    storageObjectId = bgTarget.storageObjectId;
    mediaUrl = bgTarget.url;
  }

  await ctx.api.associateMedia(ctx.productId, {
    storageObjectId,
    url: mediaUrl || undefined,
    variantId: ctx.currentVariantId,
    role,
    sortOrder,
    mediaType: 'image',
    isExternal: false,
  });
}
