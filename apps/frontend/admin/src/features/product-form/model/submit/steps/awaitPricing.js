import { ensureNotAborted, setStep } from '../state.js';

const AUTO_PUBLISH_TIMEOUT_MS = 30_000;

/**
 * Final step (auto-publish only) — wait for the pricing recompute pipeline
 * to land sellingPrices for every SKU we just generated. CAT-021 #5: we
 * can't PATCH /status straight away on auto-publish — that would race the
 * recompute and 422 on PRODUCT_NOT_READY.
 *
 * On timeout we set `ctx.autoPublishTimedOut = true` and the orchestrator
 * skips walkStatus, leaving the product as a draft with a follow-up message.
 */
export async function awaitPricing(ctx) {
  if (ctx.mode !== 'auto-publish') return;
  ensureNotAborted(ctx);
  setStep(ctx, 'awaiting_pricing');
  const allPriced = await ctx.api.waitForAllSkusPriced(ctx.productId, {
    timeout: AUTO_PUBLISH_TIMEOUT_MS,
  });
  if (!allPriced) ctx.autoPublishTimedOut = true;
}
