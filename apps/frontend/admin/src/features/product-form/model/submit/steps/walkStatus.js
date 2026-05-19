import { ensureNotAborted, setStep, SubmitError } from '../state.js';

const STATUS_LADDER = ['enriching', 'ready_for_review', 'published'];

/**
 * Final step — walk the FSM ladder DRAFT → ENRICHING → READY_FOR_REVIEW
 * → PUBLISHED. Skipped for `mode === 'draft'` and for auto-publish runs
 * that timed out waiting for the pricing recompute (the orchestrator
 * leaves them as drafts).
 *
 * Every transition gets a single retry on transient backend errors —
 * a second-attempt failure rethrows the original error so the orchestrator
 * can surface the right diagnostic.
 */
export async function walkStatus(ctx) {
  if (ctx.mode === 'draft') return;
  if (ctx.mode === 'auto-publish' && ctx.autoPublishTimedOut) return;

  ensureNotAborted(ctx);
  setStep(ctx, ctx.mode === 'auto-publish' ? 'publishing' : 'status');

  for (const target of STATUS_LADDER) {
    ensureNotAborted(ctx);
    try {
      await ctx.api.changeProductStatus(ctx.productId, target);
    } catch (firstErr) {
      try {
        await ctx.api.changeProductStatus(ctx.productId, target);
      } catch {
        throw new SubmitError({
          step: ctx.mode === 'auto-publish' ? 'publishing' : 'status',
          code: firstErr?.code ?? 'STATUS_TRANSITION_FAILED',
          message: firstErr?.message ?? `Не удалось перейти в статус ${target}`,
          recoverable: true,
          cause: firstErr,
        });
      }
    }
  }
}
