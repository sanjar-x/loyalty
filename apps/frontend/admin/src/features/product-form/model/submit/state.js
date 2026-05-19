// Submit state machine — shared types and helpers.
//
// `executeSubmit` builds a `SubmitContext` and threads it through every
// step. Each step receives the context, may mutate `ctx.state` directly,
// and either resolves (success) or throws a `SubmitError`. Recoverable
// errors (e.g. media partial failure) bubble up but the orchestrator can
// continue if the step did not abort.

export const SUBMIT_STEP_LABELS = {
  creating: 'Создание продукта...',
  attrs: 'Назначение атрибутов...',
  variants: 'Создание вариантов...',
  skus: 'Генерация SKU...',
  pricing: 'Установка цен...',
  media: 'Загрузка и обработка изображений',
  size_guide: 'Загрузка размерной сетки...',
  awaiting_pricing: 'Ждём расчёт цен (≤30 сек)…',
  status: 'Отправка на модерацию...',
  publishing: 'Публикуем товар…',
  done: 'Готово',
};

// Wrapper around the standard DOMException for aborted flows. Used so the
// orchestrator can early-return without leaking AbortError up to the UI.
export class AbortError extends Error {
  constructor(message = 'Aborted') {
    super(message);
    this.name = 'AbortError';
  }
}

// Domain error thrown by submit steps. `recoverable === true` means the
// product was created and the orchestrator can choose to continue with
// degraded state (e.g. MEDIA_PARTIAL_FAILURE — product saved as draft,
// some images missing).
export class SubmitError extends Error {
  constructor({ step, code, message, recoverable = false, cause }) {
    super(message);
    this.name = 'SubmitError';
    this.step = step;
    this.code = code;
    this.recoverable = Boolean(recoverable);
    if (cause !== undefined) this.cause = cause;
  }
}

/**
 * Build the initial submit context.
 *
 * @param {object} form         — output of useProductForm
 * @param {'draft'|'publish'|'auto-publish'} mode
 * @param {object} imageUploads — { [localId]: uploadState } from useImageUpload
 * @param {object} deps         — { signal, queryClient, api, onProgress, onStep,
 *                                  onProductCreated, onError, autosave, bgRemoval }
 */
export function createContext(
  form,
  mode = 'draft',
  imageUploads = {},
  deps = {},
) {
  return {
    form,
    mode,
    imageUploads,
    // bgRemoval is the live snapshot from useBgRemoval — the submit
    // pipeline reads stateByLocalId/variantByLocalId to decide whether
    // each image should be associated with its derived (no-background)
    // storage object or the original.
    bgRemoval: deps.bgRemoval ?? null,
    signal: deps.signal,
    queryClient: deps.queryClient,
    api: deps.api,
    onProgress: deps.onProgress ?? (() => {}),
    onStep: deps.onStep ?? (() => {}),
    onProductCreated: deps.onProductCreated ?? (() => {}),
    onError: deps.onError ?? (() => {}),
    autosave: deps.autosave ?? (() => {}),

    // Mutated by steps:
    productId: null,
    defaultVariantId: null,
    variantIndex: 0,
    currentVariantId: null,

    // Aggregated metrics:
    totalMediaCount: 0,
    totalMediaFailures: 0,

    // Auto-publish branch:
    autoPublishTimedOut: false,

    // Final result returned to the consumer.
    result: null,
  };
}

export function ensureNotAborted(ctx) {
  if (ctx.signal?.aborted) throw new AbortError();
}

export function setStep(ctx, key, message) {
  ctx.onStep(key);
  ctx.onProgress(message ?? SUBMIT_STEP_LABELS[key] ?? '');
}

// Upload-time errors that are safe to bubble through size-guide / media
// failure handling without reclassifying as a step-specific failure. When
// these fire the surrounding chain is broken regardless of which sub-step
// hit them, so the orchestrator surfaces the original error to the user.
export const TRANSIENT_PASS_THROUGH_CODES = new Set([
  'RATE_LIMITED',
  'TIMEOUT',
  'BACKEND_UNAVAILABLE',
  'SERVICE_UNAVAILABLE',
  'NETWORK_ERROR',
]);
