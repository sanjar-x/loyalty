import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { previewSkuPricing } from '../pricingPreview';

describe('previewSkuPricing', () => {
  let originalFetch;
  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = vi.fn();
  });
  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockOk(data) {
    global.fetch.mockResolvedValueOnce(
      new Response(JSON.stringify(data), { status: 200 }),
    );
  }

  it('multiplies amount to smallest currency unit and forwards the payload', async () => {
    mockOk({ finalPrice: '13750.00', contextId: 'ctx-1' });
    await previewSkuPricing({
      productId: 'p-1',
      categoryId: 'c-1',
      contextId: 'ctx-1',
      purchasePrice: { amount: 500, currency: 'CNY' },
      supplierId: 'sup-1',
    });
    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe('/api/pricing/preview-sku');
    const body = JSON.parse(init.body);
    expect(body).toEqual({
      productId: 'p-1',
      categoryId: 'c-1',
      contextId: 'ctx-1',
      purchasePrice: { amount: 50000, currency: 'CNY' },
      supplierId: 'sup-1',
    });
  });

  it('omits productId from the payload when null (CAT-023 create-flow)', async () => {
    mockOk({ finalPrice: '1086.00' });
    await previewSkuPricing({
      productId: null,
      categoryId: 'c-1',
      contextId: 'ctx-1',
      purchasePrice: { amount: 500, currency: 'CNY' },
    });
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body).not.toHaveProperty('productId');
    expect(body).toEqual({
      categoryId: 'c-1',
      contextId: 'ctx-1',
      purchasePrice: { amount: 50000, currency: 'CNY' },
    });
  });

  it('omits supplierId when not supplied', async () => {
    mockOk({ finalPrice: '1086.00' });
    await previewSkuPricing({
      productId: null,
      categoryId: 'c-1',
      contextId: 'ctx-1',
      purchasePrice: { amount: 500, currency: 'CNY' },
    });
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body).not.toHaveProperty('supplierId');
  });

  it('forwards the abort signal to the underlying request', async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    global.fetch.mockImplementationOnce(() =>
      Promise.reject(
        Object.assign(new Error('aborted'), { name: 'AbortError' }),
      ),
    );
    await expect(
      previewSkuPricing({
        productId: null,
        categoryId: 'c-1',
        contextId: 'ctx-1',
        purchasePrice: { amount: 100, currency: 'CNY' },
        signal: ctrl.signal,
      }),
    ).rejects.toMatchObject({ code: 'TIMEOUT' });
  });
});
