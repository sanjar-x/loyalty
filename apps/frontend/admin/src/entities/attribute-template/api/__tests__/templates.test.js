import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  bindAttributeToTemplate,
  fetchTemplateBindings,
  reorderTemplateBindings,
  unbindAttributeFromTemplate,
  updateTemplateBinding,
} from '../bindings';
import {
  cloneAttributeTemplate,
  createAttributeTemplate,
  fetchAttributeTemplates,
} from '../templates';

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

describe('entities/attribute-template api', () => {
  it('fetchAttributeTemplates defaults pagination', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ items: [], total: 0 })),
    );
    vi.stubGlobal('fetch', spy);
    await fetchAttributeTemplates();
    expect(spy.mock.calls[0][0]).toBe(
      '/api/catalog/attribute-templates?offset=0&limit=200',
    );
  });

  it('createAttributeTemplate POSTs the payload', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ id: 't1' }, { status: 201 })),
    );
    vi.stubGlobal('fetch', spy);
    const out = await createAttributeTemplate({
      code: 'footwear',
      nameI18N: { ru: 'Обувь', en: 'Footwear' },
      sortOrder: 0,
    });
    expect(out.id).toBe('t1');
    const [, init] = spy.mock.calls[0];
    expect(init.method).toBe('POST');
  });

  it('cloneAttributeTemplate hits /clone', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(jsonResponse({ id: 't2' }, { status: 201 })),
    );
    vi.stubGlobal('fetch', spy);
    await cloneAttributeTemplate({
      sourceTemplateId: 't1',
      newCode: 'footwear-copy',
      newNameI18N: { ru: 'Обувь (копия)', en: 'Footwear (copy)' },
    });
    expect(spy.mock.calls[0][0]).toBe('/api/catalog/attribute-templates/clone');
  });

  it('bindings CRUD hits /attributes path', async () => {
    const spy = vi.fn(() => Promise.resolve(jsonResponse({ id: 'b1' })));
    vi.stubGlobal('fetch', spy);

    await fetchTemplateBindings('t1');
    expect(spy.mock.calls[0][0]).toContain(
      '/api/catalog/attribute-templates/t1/attributes',
    );

    await bindAttributeToTemplate('t1', {
      attributeId: 'a1',
      sortOrder: 0,
      requirementLevel: 'required',
    });
    expect(spy.mock.calls[1][0]).toBe(
      '/api/catalog/attribute-templates/t1/attributes',
    );
    expect(spy.mock.calls[1][1].method).toBe('POST');

    await updateTemplateBinding('t1', 'b1', { requirementLevel: 'optional' });
    expect(spy.mock.calls[2][0]).toBe(
      '/api/catalog/attribute-templates/t1/attributes/b1',
    );
    expect(spy.mock.calls[2][1].method).toBe('PATCH');

    await unbindAttributeFromTemplate('t1', 'b1');
    expect(spy.mock.calls[3][1].method).toBe('DELETE');
  });

  it('reorderTemplateBindings wraps items', async () => {
    const spy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal('fetch', spy);
    await reorderTemplateBindings('t1', [
      { bindingId: 'b1', sortOrder: 0 },
      { bindingId: 'b2', sortOrder: 1 },
    ]);
    const [url, init] = spy.mock.calls[0];
    expect(url).toBe('/api/catalog/attribute-templates/t1/attributes/reorder');
    expect(JSON.parse(init.body).items).toHaveLength(2);
  });
});
