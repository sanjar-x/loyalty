/**
 * Contract tests for validatePublish / validateUpdate (CAT-C1.1).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { validatePublish, validateUpdate } from '../products';

const PRODUCT_ID = '019cdbf4-e987-7000-8080-000000000001';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function jsonResponse(body, init = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  });
}

describe('validatePublish', () => {
  it('POSTs to the BFF and returns the verdict + diagnostics', async () => {
    const expected = {
      ok: false,
      currentStatus: 'enriching',
      nextStatus: 'published',
      skuDiagnostics: [
        {
          skuId: 'sku-1',
          skuCode: 'AM-001',
          pricingStatus: 'missing_purchase_price',
          hasManualPrice: false,
          hasSellingPrice: false,
          hasPurchasePrice: false,
          failureReason: null,
          nextStep: 'Введите закупочную цену',
        },
      ],
      gateFailures: [{ code: 'AT_LEAST_ONE_PUBLISHABLE_SKU', context: {} }],
    };
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(expected)));
    vi.stubGlobal('fetch', fetchMock);

    const data = await validatePublish(PRODUCT_ID);
    expect(data).toEqual(expected);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/catalog/products/${PRODUCT_ID}/validate-publish`);
    expect(init.method).toBe('POST');
  });

  it('returns ok=true when there are no gate failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          jsonResponse({
            ok: true,
            currentStatus: 'enriching',
            nextStatus: 'published',
            skuDiagnostics: [],
            gateFailures: [],
          }),
        ),
      ),
    );
    const data = await validatePublish(PRODUCT_ID);
    expect(data.ok).toBe(true);
    expect(data.gateFailures).toEqual([]);
  });
});

describe('validateUpdate', () => {
  it('POSTs the same payload shape as PATCH /products/:id', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        jsonResponse({
          ok: true,
          diff: [
            {
              field: 'supplierId',
              before: 'sup-old',
              after: 'sup-new',
            },
          ],
          warnings: [
            {
              code: 'SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE',
              message: 'Supplier change will recompute 5 SKUs',
              context: { affectedCount: 5 },
            },
          ],
          validationErrors: [],
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const data = await validateUpdate(PRODUCT_ID, { supplierId: 'sup-new' });
    expect(data.ok).toBe(true);
    expect(data.warnings[0].code).toBe('SUPPLIER_CHANGE_TRIGGERS_RECOMPUTE');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/catalog/products/${PRODUCT_ID}/validate-update`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ supplierId: 'sup-new' });
  });
});
