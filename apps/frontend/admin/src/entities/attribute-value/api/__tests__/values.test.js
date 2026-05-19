import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  activateAttributeValue,
  bulkAddAttributeValues,
  createAttributeValue,
  deactivateAttributeValue,
  fetchAttributeValues,
  reorderAttributeValues,
} from '../values';

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

describe('entities/attribute-value api', () => {
  it('fetchAttributeValues forwards isActive only when explicitly set', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ items: [], total: 0 })),
    );
    vi.stubGlobal('fetch', spy);
    await fetchAttributeValues('a1', { isActive: false });
    expect(spy.mock.calls[0][0]).toContain('isActive=false');

    await fetchAttributeValues('a1', { isActive: '' });
    expect(spy.mock.calls[1][0]).not.toContain('isActive=');
  });

  it('createAttributeValue posts under the parent', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ id: 'v1' }, { status: 201 })),
    );
    vi.stubGlobal('fetch', spy);
    await createAttributeValue('a1', {
      code: 'red',
      slug: 'red',
      valueI18N: { ru: 'Красный', en: 'Red' },
      searchAliases: [],
      metaData: { hex: '#FF0000' },
      sortOrder: 0,
    });
    expect(spy.mock.calls[0][0]).toBe('/api/catalog/attributes/a1/values');
    expect(spy.mock.calls[0][1].method).toBe('POST');
  });

  it('deactivate / activate hit the dedicated endpoints', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ id: 'v1', isActive: false })),
    );
    vi.stubGlobal('fetch', spy);
    await deactivateAttributeValue('a1', 'v1');
    expect(spy.mock.calls[0][0]).toBe(
      '/api/catalog/attributes/a1/values/v1/deactivate',
    );

    await activateAttributeValue('a1', 'v1');
    expect(spy.mock.calls[1][0]).toBe(
      '/api/catalog/attributes/a1/values/v1/activate',
    );
  });

  it('bulkAddAttributeValues wraps items into the request envelope', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ createdCount: 1, ids: ['v1'] }, { status: 201 }),
      ),
    );
    vi.stubGlobal('fetch', spy);
    await bulkAddAttributeValues('a1', [{ code: 'red' }]);
    expect(JSON.parse(spy.mock.calls[0][1].body)).toEqual({
      items: [{ code: 'red' }],
    });
  });

  it('reorderAttributeValues wraps items into the request envelope', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal('fetch', spy);
    await reorderAttributeValues('a1', [{ valueId: 'v1', sortOrder: 0 }]);
    expect(JSON.parse(spy.mock.calls[0][1].body)).toEqual({
      items: [{ valueId: 'v1', sortOrder: 0 }],
    });
  });
});
