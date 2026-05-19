/**
 * Attribute API smoke — pins the BFF URL shapes + payload allow-list
 * the rest of the slice depends on. Stubs `global.fetch` since the
 * apiClient lives in the same `shared/api` layer that all other slices
 * already cover with end-to-end tests.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  bulkCreateAttributes,
  createAttribute,
  deleteAttribute,
  fetchAttributes,
  getAttributeUsage,
  updateAttribute,
} from '../attributes';

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

function stub(spy) {
  vi.stubGlobal('fetch', spy);
}

describe('entities/attribute api', () => {
  it('fetchAttributes appends only non-empty filters', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ items: [], total: 0 })),
    );
    stub(spy);
    await fetchAttributes({
      level: 'product',
      isDictionary: true,
      groupId: '',
    });
    const [url] = spy.mock.calls[0];
    expect(url).toContain('/api/catalog/attributes?');
    expect(url).toContain('level=product');
    expect(url).toContain('isDictionary=true');
    expect(url).not.toContain('groupId=');
  });

  it('createAttribute POSTs the payload verbatim', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ id: 'a1' }, { status: 201 })),
    );
    stub(spy);
    const payload = {
      code: 'color',
      slug: 'color',
      nameI18N: { ru: 'Цвет', en: 'Color' },
      dataType: 'string',
      uiType: 'color_swatch',
    };
    const out = await createAttribute(payload);
    expect(out.id).toBe('a1');
    const [, init] = spy.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual(payload);
  });

  it('updateAttribute PATCHes the immutable-safe subset', async () => {
    const spy = vi.fn(() => Promise.resolve(jsonResponse({ id: 'a1' })));
    stub(spy);
    await updateAttribute('a1', { uiType: 'dropdown' });
    const [url, init] = spy.mock.calls[0];
    expect(url).toBe('/api/catalog/attributes/a1');
    expect(init.method).toBe('PATCH');
  });

  it('deleteAttribute DELETEs by id', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    stub(spy);
    await deleteAttribute('a1');
    const [url, init] = spy.mock.calls[0];
    expect(url).toBe('/api/catalog/attributes/a1');
    expect(init.method).toBe('DELETE');
  });

  it('getAttributeUsage hits the analytics path', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(
        jsonResponse({
          templateCount: 0,
          templates: [],
          categoryCount: 0,
          categories: [],
          productCount: 0,
        }),
      ),
    );
    stub(spy);
    const out = await getAttributeUsage('a1');
    expect(out.templateCount).toBe(0);
    expect(spy.mock.calls[0][0]).toBe('/api/catalog/attributes/a1/usage');
  });

  it('bulkCreateAttributes always sends skipExisting', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(
        jsonResponse(
          { createdCount: 1, skippedCount: 0, ids: ['a1'], skippedCodes: [] },
          { status: 201 },
        ),
      ),
    );
    stub(spy);
    await bulkCreateAttributes({ items: [{ code: 'x' }] });
    const [, init] = spy.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({
      items: [{ code: 'x' }],
      skipExisting: false,
    });
  });
});
