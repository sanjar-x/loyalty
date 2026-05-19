// Lightweight localStorage-backed draft autosave for the product create form.
//
// Drafts are keyed by `categoryId` + `slug` (or `'untitled'` if the user
// hasn't entered a slug yet). Saved after every successful submit step so
// a tab crash mid-flow doesn't lose what the user typed; cleared once the
// orchestrator finishes successfully.
//
// Storage layout:
//
//   localStorage[draftKey(categoryId, slug)] = JSON.stringify({
//     savedAt: <ISO>,
//     lastStep: <step-name>,
//     productId: string|null,
//     defaultVariantId: string|null,
//     formState: form.state,
//   })

const PREFIX = 'product-form-draft';

export function draftKey(categoryId, slug) {
  return `${PREFIX}:${categoryId ?? 'no-category'}:${slug || 'untitled'}`;
}

function safeStorage() {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function saveDraft(ctx, stepName) {
  const storage = safeStorage();
  if (!storage) return;
  const state = ctx.form?.state;
  if (!state) return;
  const key = draftKey(state.categoryId, state.slug);
  const payload = {
    savedAt: new Date().toISOString(),
    lastStep: stepName,
    productId: ctx.productId,
    defaultVariantId: ctx.defaultVariantId,
    formState: serialiseFormState(state),
  };
  try {
    storage.setItem(key, JSON.stringify(payload));
  } catch {
    /* quota / private mode — autosave is best-effort */
  }
}

export function loadDraft(categoryId, slug) {
  const storage = safeStorage();
  if (!storage) return null;
  try {
    const raw = storage.getItem(draftKey(categoryId, slug));
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearDraft(ctx) {
  const storage = safeStorage();
  if (!storage) return;
  const state = ctx.form?.state;
  if (!state) return;
  try {
    storage.removeItem(draftKey(state.categoryId, state.slug));
  } catch {
    /* noop */
  }
}

// `File` and `Blob` instances aren't JSON-serialisable. Strip them before
// persisting; the "восстановить черновик" UI can re-prompt the user to
// re-attach files instead of trying to reconstruct them.
function serialiseFormState(state) {
  const variants = (state.variants ?? []).map((variant) => ({
    ...variant,
    images: (variant.images ?? []).map(stripFileFields),
    sizeGuide: variant.sizeGuide ? stripFileFields(variant.sizeGuide) : null,
  }));
  return { ...state, variants };
}

function stripFileFields(image) {
  if (!image) return image;
  // Drop `file` (a File instance) and any blob: URL — those don't survive
  // a tab reload and must be re-attached. Keep storageObjectId/url so an
  // eager-uploaded image is recognised on reload.
  const { file: _file, ...rest } = image;
  void _file;
  if (typeof rest.url === 'string' && rest.url.startsWith('blob:')) {
    rest.url = null;
  }
  return rest;
}
