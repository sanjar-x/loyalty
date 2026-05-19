/**
 * Autosave tests — verify localStorage round-trip, blob:// stripping,
 * and clearDraft after success.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { clearDraft, draftKey, loadDraft, saveDraft } from '../autosave';

function makeCtx(overrides = {}) {
  return {
    productId: 'prod-1',
    defaultVariantId: 'var-default',
    form: {
      state: {
        categoryId: 'cat-1',
        slug: 'air-max-90',
        variants: [
          {
            variantAttrs: {},
            images: [
              {
                localId: 'img-1',
                file: new Blob(['x'], { type: 'image/jpeg' }),
                url: 'blob:http://localhost/abc',
                storageObjectId: null,
              },
              {
                localId: 'img-2',
                file: null,
                url: 'https://cdn/permanent.webp',
                storageObjectId: 'sid-2',
              },
            ],
            sizeGuide: {
              file: new Blob(['x']),
              url: 'blob:http://localhost/sg',
            },
          },
        ],
      },
    },
    ...overrides,
  };
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});

describe('autosave', () => {
  it('builds a stable draft key', () => {
    expect(draftKey('cat-1', 'air-max-90')).toBe(
      'product-form-draft:cat-1:air-max-90',
    );
    expect(draftKey(null, '')).toBe('product-form-draft:no-category:untitled');
  });

  it('saveDraft strips File instances and blob: URLs', () => {
    const ctx = makeCtx();
    saveDraft(ctx, 'creating');
    const stored = JSON.parse(
      window.localStorage.getItem('product-form-draft:cat-1:air-max-90'),
    );
    expect(stored.productId).toBe('prod-1');
    expect(stored.lastStep).toBe('creating');
    const variant = stored.formState.variants[0];
    expect(variant.images).toHaveLength(2);
    // First image had blob: + File — both stripped.
    expect(variant.images[0]).not.toHaveProperty('file');
    expect(variant.images[0].url).toBeNull();
    // Second image had a permanent URL — kept as-is.
    expect(variant.images[1].url).toBe('https://cdn/permanent.webp');
    expect(variant.images[1].storageObjectId).toBe('sid-2');
    // Size guide was a blob — stripped down to a JSON-safe shape.
    expect(variant.sizeGuide).not.toHaveProperty('file');
    expect(variant.sizeGuide.url).toBeNull();
  });

  it('loadDraft round-trips a saved payload', () => {
    saveDraft(makeCtx(), 'attrs');
    const loaded = loadDraft('cat-1', 'air-max-90');
    expect(loaded.productId).toBe('prod-1');
    expect(loaded.formState.slug).toBe('air-max-90');
  });

  it('clearDraft removes the entry', () => {
    saveDraft(makeCtx(), 'attrs');
    expect(loadDraft('cat-1', 'air-max-90')).not.toBeNull();
    clearDraft(makeCtx());
    expect(loadDraft('cat-1', 'air-max-90')).toBeNull();
  });

  it('saveDraft is a no-op when localStorage rejects', () => {
    const original = window.localStorage.setItem;
    window.localStorage.setItem = () => {
      throw new Error('quota');
    };
    expect(() => saveDraft(makeCtx(), 'creating')).not.toThrow();
    window.localStorage.setItem = original;
  });
});
