import { productKeys } from '@/entities/product';

import {
  AbortError,
  createContext,
  ensureNotAborted,
  setStep,
  SubmitError,
} from './state.js';
import { applyPricing } from './steps/applyPricing.js';
import { awaitPricing } from './steps/awaitPricing.js';
import { bulkAttrs } from './steps/bulkAttrs.js';
import { createProduct } from './steps/createProduct.js';
import { createVariants } from './steps/createVariants.js';
import { generateSkus } from './steps/generateSkus.js';
import { uploadMedia } from './steps/uploadMedia.js';
import { uploadSizeGuide } from './steps/uploadSizeGuide.js';
import { walkStatus } from './steps/walkStatus.js';
import { clearDraft, saveDraft } from './autosave.js';

// Steps that run once at the top of the chain.
const TOP_STEPS = [
  { name: 'creating', run: createProduct },
  { name: 'attrs', run: bulkAttrs },
];

// Steps that run in lock-step for every variant.
const PER_VARIANT_STEPS = [
  { name: 'variants', run: createVariants },
  { name: 'skus', run: generateSkus },
  { name: 'pricing', run: applyPricing },
  { name: 'media', run: uploadMedia },
  { name: 'size_guide', run: uploadSizeGuide },
];

// Steps that run once after every variant has been processed.
const FINAL_STEPS = [
  { name: 'awaiting_pricing', run: awaitPricing },
  { name: 'walking_status', run: walkStatus },
];

/**
 * Drive the create-product submit flow.
 *
 * `deps.api` must mirror the surface used by every step:
 *
 *   createProduct, bulkAssignAttrs, createVariant, generateSkus,
 *   listSkus, updateSku, reserveMediaUpload, uploadToS3, confirmMedia,
 *   subscribeMediaStatus, fetchImageAsFile, extractRawUrl,
 *   associateMedia, waitForAllSkusPriced, changeProductStatus.
 *
 * The default useSubmitProduct wires this up against `@/entities/product`.
 */
export async function executeSubmit(form, mode, imageUploads, deps) {
  // `deps.bgRemoval` is the live snapshot from useBgRemoval — when present
  // the per-variant uploadMedia step swaps in the derived (no-background)
  // storage object for any image the merchandiser toggled to 'no-background'.
  const ctx = createContext(form, mode, imageUploads, deps);

  try {
    // Top-level steps.
    for (const step of TOP_STEPS) {
      ensureNotAborted(ctx);
      await step.run(ctx);
      saveDraftAfterStep(ctx, step.name);
    }

    // Per-variant pipeline.
    const variants = form.state.variants ?? [];
    for (let vi = 0; vi < variants.length; vi += 1) {
      ctx.variantIndex = vi;
      for (const step of PER_VARIANT_STEPS) {
        ensureNotAborted(ctx);
        await step.run(ctx);
        saveDraftAfterStep(ctx, step.name);
      }
    }

    // Aggregate media outcome — bubble up as a single recoverable error
    // when any image failed to upload across any variant. Matches the
    // legacy useSubmitProduct contract.
    if (ctx.totalMediaFailures > 0) {
      throw new SubmitError({
        step: 'media',
        code: 'MEDIA_PARTIAL_FAILURE',
        message: `${ctx.totalMediaFailures} из ${ctx.totalMediaCount} изображений не загрузились. Продукт создан как черновик.`,
        recoverable: true,
      });
    }

    // Final steps (auto-publish wait + status walk).
    for (const step of FINAL_STEPS) {
      ensureNotAborted(ctx);
      await step.run(ctx);
    }

    setStep(ctx, 'done');

    if (deps.queryClient) {
      await deps.queryClient.invalidateQueries({
        queryKey: productKeys.lists(),
      });
    }

    clearDraft(ctx);

    ctx.result = buildResult(ctx);
    return ctx.result;
  } catch (err) {
    if (err instanceof AbortError || err?.name === 'AbortError') {
      // Aborted — bubble up; the consumer hook surfaces a dedicated
      // ABORTED_AFTER_CREATE message when productId is set.
      throw err;
    }
    // Last-ditch wrap: unknown errors become SubmitError so the consumer
    // can rely on `.step` / `.code` always being present.
    if (!(err instanceof SubmitError)) {
      throw new SubmitError({
        step: 'unknown',
        code: err?.code ?? 'UNKNOWN',
        message: err?.message ?? 'Неизвестная ошибка',
        cause: err,
      });
    }
    throw err;
  }
}

function buildResult(ctx) {
  return {
    productId: ctx.productId,
    defaultVariantId: ctx.defaultVariantId,
    autoPublishTimedOut: ctx.autoPublishTimedOut || undefined,
  };
}

function saveDraftAfterStep(ctx, stepName) {
  // Autosave is opt-in and best-effort; orchestrator must not throw on
  // localStorage failures (quota, private mode). The `autosave` dep is a
  // function provided by the consumer; default no-op when missing.
  try {
    saveDraft(ctx, stepName);
  } catch {
    /* noop */
  }
}
