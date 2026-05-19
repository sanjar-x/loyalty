/**
 * Integration tests for <AttributeFormModal>: locks the create-mode
 * payload shape (code/slug/dataType/uiType + i18n + flags) and the
 * edit-mode read-only fields. Backend BFF + apiClient round-trip is
 * stubbed via `global.fetch`.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { AttributeFormModal } from '../AttributeFormModal';

const SAMPLE_GROUPS = {
  items: [
    {
      id: 'g1',
      code: 'physical',
      nameI18N: { ru: 'Физика', en: 'Physical' },
      sortOrder: 0,
    },
  ],
  total: 1,
};

const SAMPLE_ATTRIBUTE = {
  id: 'a1',
  code: 'color',
  slug: 'color',
  nameI18N: { ru: 'Цвет', en: 'Color' },
  descriptionI18N: { ru: '', en: '' },
  dataType: 'string',
  uiType: 'color_swatch',
  isDictionary: true,
  groupId: 'g1',
  level: 'variant',
  isFilterable: true,
  isSearchable: false,
  searchWeight: 5,
  isComparable: false,
  isVisibleOnCard: true,
  validationRules: null,
};

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, staleTime: 0 },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  }
  return { client, Wrapper };
}

function stubFetch(handlers) {
  const calls = [];
  const handler = vi.fn((url, init) => {
    const u = String(url);
    calls.push({ url: u, init });
    for (const [match, response] of handlers) {
      if (u.includes(match)) return response();
    }
    return Promise.reject(new Error(`Unhandled fetch: ${u}`));
  });
  vi.stubGlobal('fetch', handler);
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('<AttributeFormModal> create', () => {
  it('submits a fully-populated payload', async () => {
    const onClose = vi.fn();
    const calls = stubFetch([
      [
        '/api/catalog/attribute-groups',
        () =>
          Promise.resolve(
            new Response(JSON.stringify(SAMPLE_GROUPS), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }),
          ),
      ],
      [
        '/api/catalog/attributes',
        () =>
          Promise.resolve(
            new Response(JSON.stringify({ id: 'a-new' }), {
              status: 201,
              headers: { 'Content-Type': 'application/json' },
            }),
          ),
      ],
    ]);

    const { Wrapper } = makeWrapper();
    render(<AttributeFormModal open mode="create" onClose={onClose} />, {
      wrapper: Wrapper,
    });

    // Both `code` and `slug` use the same placeholder; address each
    // by index since testing-library otherwise returns multiple.
    const sameNamed = screen.getAllByPlaceholderText('color');
    fireEvent.change(sameNamed[0], { target: { value: 'color' } });
    fireEvent.change(sameNamed[1], { target: { value: 'color' } });
    fireEvent.change(screen.getByPlaceholderText('Цвет'), {
      target: { value: 'Цвет' },
    });
    fireEvent.change(screen.getByPlaceholderText('Color'), {
      target: { value: 'Color' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Создать$/ }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());

    const createCall = calls.find(
      (c) => c.url === '/api/catalog/attributes' && c.init.method === 'POST',
    );
    expect(createCall).toBeDefined();
    const body = JSON.parse(createCall.init.body);
    expect(body.code).toBe('color');
    expect(body.slug).toBe('color');
    expect(body.dataType).toBe('string');
    expect(body.uiType).toBe('dropdown');
    expect(body.nameI18N).toEqual({ ru: 'Цвет', en: 'Color' });
    expect(body.isDictionary).toBe(true);
  });

  it('disables submit when slug regex fails', async () => {
    stubFetch([
      [
        '/api/catalog/attribute-groups',
        () =>
          Promise.resolve(
            new Response(JSON.stringify(SAMPLE_GROUPS), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }),
          ),
      ],
    ]);
    const { Wrapper } = makeWrapper();
    render(<AttributeFormModal open mode="create" onClose={vi.fn()} />, {
      wrapper: Wrapper,
    });

    const fields = screen.getAllByPlaceholderText('color');
    fireEvent.change(fields[0], {
      target: { value: 'Color With Spaces' },
    });
    fireEvent.change(fields[1], { target: { value: 'Bad Slug' } });

    expect(screen.getByRole('button', { name: /Создать$/ })).toBeDisabled();
    // Regex error message surfaces inline.
    expect(screen.getAllByText(/нижний регистр/).length).toBeGreaterThan(0);
  });
});

describe('<AttributeFormModal> edit', () => {
  it('disables immutable fields and patches the editable subset', async () => {
    const onClose = vi.fn();
    const calls = stubFetch([
      [
        '/api/catalog/attribute-groups',
        () =>
          Promise.resolve(
            new Response(JSON.stringify(SAMPLE_GROUPS), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }),
          ),
      ],
      [
        '/api/catalog/attributes/a1',
        () =>
          Promise.resolve(
            new Response(JSON.stringify({ id: 'a1' }), {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }),
          ),
      ],
    ]);
    const { Wrapper } = makeWrapper();
    render(
      <AttributeFormModal
        open
        mode="edit"
        attribute={SAMPLE_ATTRIBUTE}
        onClose={onClose}
      />,
      { wrapper: Wrapper },
    );

    // `code` / `slug` / `dataType` / `Справочник` are disabled in edit
    // mode — guard so backend never has to rebuff a 422.
    const codeAndSlug = screen.getAllByDisplayValue('color');
    expect(codeAndSlug).toHaveLength(2);
    for (const input of codeAndSlug) expect(input).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: /Сохранить/ }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());

    const patchCall = calls.find(
      (c) =>
        c.url === '/api/catalog/attributes/a1' && c.init.method === 'PATCH',
    );
    expect(patchCall).toBeDefined();
    const body = JSON.parse(patchCall.init.body);
    expect(body.code).toBeUndefined();
    expect(body.slug).toBeUndefined();
    expect(body.dataType).toBeUndefined();
    expect(body.uiType).toBe('color_swatch');
    expect(body.level).toBe('variant');
    expect(body.isFilterable).toBe(true);
  });
});
