import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createAttributeGroup,
  deleteAttributeGroup,
  fetchAttributeGroups,
  updateAttributeGroup,
} from '../groups';

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

describe('entities/attribute-group api', () => {
  it('fetchAttributeGroups defaults pagination', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ items: [], total: 0 })),
    );
    vi.stubGlobal('fetch', spy);
    await fetchAttributeGroups();
    expect(spy.mock.calls[0][0]).toBe(
      '/api/catalog/attribute-groups?offset=0&limit=200',
    );
  });

  it('createAttributeGroup POSTs payload', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ id: 'g1' }, { status: 201 })),
    );
    vi.stubGlobal('fetch', spy);
    const out = await createAttributeGroup({
      code: 'physical',
      nameI18N: { ru: 'Физика', en: 'Physical' },
      sortOrder: 0,
    });
    expect(out.id).toBe('g1');
    expect(spy.mock.calls[0][1].method).toBe('POST');
  });

  it('updateAttributeGroup hits the per-id PATCH', async () => {
    const spy = vi.fn(() => Promise.resolve(jsonResponse({ id: 'g1' })));
    vi.stubGlobal('fetch', spy);
    await updateAttributeGroup('g1', { sortOrder: 5 });
    const [url, init] = spy.mock.calls[0];
    expect(url).toBe('/api/catalog/attribute-groups/g1');
    expect(init.method).toBe('PATCH');
    expect(JSON.parse(init.body)).toEqual({ sortOrder: 5 });
  });

  it('deleteAttributeGroup DELETEs by id', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal('fetch', spy);
    await deleteAttributeGroup('g1');
    const [url, init] = spy.mock.calls[0];
    expect(url).toBe('/api/catalog/attribute-groups/g1');
    expect(init.method).toBe('DELETE');
  });
});
