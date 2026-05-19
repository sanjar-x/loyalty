/**
 * Orchestrator integration tests — exercise the executeSubmit cycle with
 * a fully-mocked API surface so we lock the contract:
 *   1. step ordering (top → per-variant × N → final)
 *   2. variant skipping (vi > 0 with empty form skips the per-variant chain)
 *   3. signal propagation (abort surfaces as AbortError)
 *   4. recoverable errors return through their step (SubmitError)
 *   5. media partial-failure aggregates across variants
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { executeSubmit } from '../orchestrator';
import { AbortError, SubmitError } from '../state';

function makeApi(overrides = {}) {
  const base = {
    createProduct: vi.fn(async () => ({
      id: 'prod-1',
      defaultVariantId: 'var-default',
    })),
    bulkAssignAttrs: vi.fn(async () => ({})),
    createVariant: vi.fn(async () => ({ id: 'var-extra' })),
    generateSkus: vi.fn(async () => ({ createdCount: 1, skippedCount: 0 })),
    listSkus: vi.fn(async () => ({ items: [] })),
    updateSku: vi.fn(async () => ({})),
    reserveMediaUpload: vi.fn(async () => ({
      presignedUrl: 'https://s3/upload?sig',
      storageObjectId: 'sid-1',
    })),
    uploadToS3: vi.fn(async () => undefined),
    confirmMedia: vi.fn(async () => undefined),
    subscribeMediaStatus: vi.fn(async () => ({
      status: 'COMPLETED',
      url: 'https://cdn/img.webp',
    })),
    fetchImageAsFile: vi.fn(async () => ({
      name: 'x.jpg',
      type: 'image/jpeg',
    })),
    extractRawUrl: vi.fn(() => 'https://cdn/raw.jpg'),
    associateMedia: vi.fn(async () => ({ id: 'media-1' })),
    waitForAllSkusPriced: vi.fn(async () => true),
    changeProductStatus: vi.fn(async () => ({})),
  };
  return { ...base, ...overrides };
}

function makeForm({ variantCount = 1, withMedia = false, payload = {} } = {}) {
  const variants = Array.from({ length: variantCount }, (_, i) => ({
    variantAttrs: i === 0 ? { 'attr-1': ['val-1'] } : {},
    images:
      withMedia && i === 0
        ? [{ localId: `img-${i}`, file: { name: 'a.jpg', type: 'image/jpeg' } }]
        : [],
    sizeGuide: null,
    // Only the first variant carries price input. Additional variants
    // start "empty" so the createVariants step short-circuits unless the
    // test populates them explicitly.
    price: i === 0 ? { amount: 1000 } : null,
    purchasePrice: null,
  }));

  const variantPayloads = variants.map((v, i) => ({
    skuGeneratePayload:
      i === 0
        ? {
            attributeSelections: [
              { attributeId: 'attr-1', valueIds: ['val-1'] },
            ],
            price: { amount: 100000, currency: 'RUB' },
          }
        : null,
    perSkuPriceUpdates: [],
    variantPurchasePrice: null,
  }));

  return {
    state: { variants, slug: 'slug-1', categoryId: 'cat-1' },
    productPayload: {
      titleI18N: { ru: 'X', en: 'X' },
      slug: 'slug-1',
      brandId: 'brand-1',
      primaryCategoryId: 'cat-1',
    },
    bulkAttrsPayload: payload.bulkAttrsPayload ?? null,
    variantPayloads,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('executeSubmit — happy paths', () => {
  it('runs draft mode end-to-end without status walk', async () => {
    const api = makeApi();
    const result = await executeSubmit(
      makeForm(),
      'draft',
      {},
      { api, signal: undefined },
    );
    expect(result).toEqual({
      productId: 'prod-1',
      defaultVariantId: 'var-default',
      autoPublishTimedOut: undefined,
    });
    expect(api.createProduct).toHaveBeenCalledTimes(1);
    expect(api.generateSkus).toHaveBeenCalledTimes(1);
    expect(api.changeProductStatus).not.toHaveBeenCalled();
    expect(api.waitForAllSkusPriced).not.toHaveBeenCalled();
  });

  it('publish mode walks the FSM ladder', async () => {
    const api = makeApi();
    await executeSubmit(makeForm(), 'publish', {}, { api });
    const calls = api.changeProductStatus.mock.calls.map((c) => c[1]);
    expect(calls).toEqual(['enriching', 'ready_for_review', 'published']);
  });

  it('auto-publish waits for pricing then walks the ladder', async () => {
    const api = makeApi();
    await executeSubmit(makeForm(), 'auto-publish', {}, { api });
    expect(api.waitForAllSkusPriced).toHaveBeenCalledTimes(1);
    expect(api.changeProductStatus).toHaveBeenCalledTimes(3);
  });

  it('auto-publish with timeout leaves the product as draft', async () => {
    const api = makeApi({
      waitForAllSkusPriced: vi.fn(async () => false),
    });
    const result = await executeSubmit(makeForm(), 'auto-publish', {}, { api });
    expect(api.changeProductStatus).not.toHaveBeenCalled();
    expect(result.autoPublishTimedOut).toBe(true);
  });
});

describe('executeSubmit — variant fan-out', () => {
  it('reuses defaultVariantId for index 0 and POSTs createVariant for >0', async () => {
    const api = makeApi();
    const form = makeForm({ variantCount: 2 });
    // Mark second variant non-empty so it doesn't get skipped.
    form.state.variants[1].variantAttrs = { 'attr-1': ['val-2'] };
    form.variantPayloads[1].skuGeneratePayload = {
      attributeSelections: [{ attributeId: 'attr-1', valueIds: ['val-2'] }],
      price: { amount: 100000, currency: 'RUB' },
    };

    await executeSubmit(form, 'draft', {}, { api });

    expect(api.createVariant).toHaveBeenCalledTimes(1);
    // generateSkus runs twice: once for default variant, once for the
    // newly-created one. Verify both variant ids used.
    const variantIdsUsed = api.generateSkus.mock.calls.map((c) => c[1]);
    expect(variantIdsUsed).toEqual(['var-default', 'var-extra']);
  });

  it('skips empty additional variants entirely', async () => {
    const api = makeApi();
    const form = makeForm({ variantCount: 2 });
    // Variant 1 stays empty by default in makeForm.
    await executeSubmit(form, 'draft', {}, { api });
    expect(api.createVariant).not.toHaveBeenCalled();
    expect(api.generateSkus).toHaveBeenCalledTimes(1);
  });
});

describe('executeSubmit — abort propagation', () => {
  it('throws AbortError when signal is already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    const api = makeApi();
    await expect(
      executeSubmit(
        makeForm(),
        'draft',
        {},
        {
          api,
          signal: controller.signal,
        },
      ),
    ).rejects.toBeInstanceOf(AbortError);
  });

  it('aborts mid-flow once the signal flips', async () => {
    const controller = new AbortController();
    const api = makeApi({
      bulkAssignAttrs: vi.fn(async () => {
        controller.abort();
      }),
    });
    const form = makeForm({ payload: { bulkAttrsPayload: { items: [{}] } } });
    await expect(
      executeSubmit(form, 'draft', {}, { api, signal: controller.signal }),
    ).rejects.toBeInstanceOf(AbortError);
    // Variant pipeline must not run after the abort.
    expect(api.generateSkus).not.toHaveBeenCalled();
  });
});

describe('executeSubmit — error classification', () => {
  it('wraps unknown step errors into SubmitError', async () => {
    const api = makeApi({
      createProduct: vi.fn(async () => {
        const err = new Error('boom');
        err.code = 'BAD_THINGS';
        throw err;
      }),
    });
    await expect(
      executeSubmit(makeForm(), 'draft', {}, { api }),
    ).rejects.toMatchObject({
      name: 'SubmitError',
      step: 'creating',
      code: 'BAD_THINGS',
    });
  });

  it('aggregates media failures across variants into MEDIA_PARTIAL_FAILURE', async () => {
    const api = makeApi({
      // The first associateMedia rejects; the upload chain catches via
      // Promise.allSettled inside uploadMedia, so the orchestrator only
      // sees the aggregated failure count.
      associateMedia: vi.fn(async () => {
        throw new Error('S3 down');
      }),
    });
    const form = makeForm({ withMedia: true });
    await expect(
      executeSubmit(form, 'draft', { 'img-0': null }, { api }),
    ).rejects.toMatchObject({
      name: 'SubmitError',
      code: 'MEDIA_PARTIAL_FAILURE',
      step: 'media',
      recoverable: true,
    });
  });

  it('treats ZERO_SKUS as a recoverable SubmitError', async () => {
    const api = makeApi({
      generateSkus: vi.fn(async () => ({
        createdCount: 0,
        skippedCount: 0,
      })),
    });
    await expect(
      executeSubmit(makeForm(), 'draft', {}, { api }),
    ).rejects.toMatchObject({
      name: 'SubmitError',
      code: 'ZERO_SKUS',
      recoverable: true,
    });
  });
});

describe('executeSubmit — onStep wiring', () => {
  it('emits step transitions in the documented order', async () => {
    const seen = [];
    const api = makeApi();
    const form = makeForm({ payload: { bulkAttrsPayload: { items: [{}] } } });
    await executeSubmit(
      form,
      'publish',
      {},
      {
        api,
        onStep: (s) => seen.push(s),
      },
    );
    expect(seen).toEqual(['creating', 'attrs', 'skus', 'status', 'done']);
  });
});
