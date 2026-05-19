/**
 * Integration test for the BindingsList DnD reorder + per-row
 * requirement-level toggle. The bindings query is pre-seeded into
 * the QueryClient so the list renders synchronously; the reorder
 * fetch is captured to verify the payload shape.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';

import { attributeTemplateKeys } from '@/entities/attribute-template';

import { BindingsList } from '../BindingsList';

const TEMPLATE_ID = 't1';

const SAMPLE_BINDINGS = {
  items: [
    {
      id: 'b1',
      templateId: TEMPLATE_ID,
      attributeId: 'a-color',
      sortOrder: 0,
      requirementLevel: 'required',
      attributeCode: 'color',
      attributeNameI18N: { ru: 'Цвет', en: 'Color' },
      attributeDataType: 'string',
      attributeUiType: 'color_swatch',
      attributeLevel: 'variant',
      attributeIsFilterable: true,
    },
    {
      id: 'b2',
      templateId: TEMPLATE_ID,
      attributeId: 'a-size',
      sortOrder: 1,
      requirementLevel: 'recommended',
      attributeCode: 'size',
      attributeNameI18N: { ru: 'Размер', en: 'Size' },
      attributeDataType: 'string',
      attributeUiType: 'dropdown',
      attributeLevel: 'variant',
      attributeIsFilterable: true,
    },
  ],
  total: 2,
};

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity, staleTime: Infinity },
      mutations: { retry: false },
    },
  });
  client.setQueryData(
    attributeTemplateKeys.bindings(TEMPLATE_ID),
    SAMPLE_BINDINGS,
  );
  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  }
  return { client, Wrapper };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('<BindingsList>', () => {
  it('renders bindings sorted by sortOrder with requirement labels', () => {
    const { Wrapper } = makeWrapper();
    render(<BindingsList templateId={TEMPLATE_ID} />, { wrapper: Wrapper });

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByText('Цвет')).toBeInTheDocument();
    expect(within(items[1]).getByText('Размер')).toBeInTheDocument();

    // Both the pill and the select <option> render the same RU label,
    // so the assertion uses the requirement-level select to read the
    // currently-applied value per row.
    const selects = screen.getAllByLabelText('Уровень требования');
    expect(selects[0]).toHaveValue('required');
    expect(selects[1]).toHaveValue('recommended');
  });

  it('keyboard Alt+ArrowDown reorders the binding and POSTs the new order', async () => {
    const fetchSpy = vi.fn(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    );
    vi.stubGlobal('fetch', fetchSpy);

    const { Wrapper } = makeWrapper();
    render(<BindingsList templateId={TEMPLATE_ID} />, { wrapper: Wrapper });

    const items = screen.getAllByRole('listitem');
    items[0].focus();
    fireEvent.keyDown(items[0], { key: 'ArrowDown', altKey: true });

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(([url]) => String(url).includes('/reorder')),
      ).toBe(true),
    );
    const reorderCall = fetchSpy.mock.calls.find(([url]) =>
      String(url).includes('/reorder'),
    );
    const body = JSON.parse(reorderCall[1].body);
    expect(body.items).toEqual([
      { bindingId: 'b2', sortOrder: 0 },
      { bindingId: 'b1', sortOrder: 1 },
    ]);

    // Audit 9.1 — sr-only live region must announce the move so the
    // screen-reader path matches the pointer path.
    const announcer = screen.getByRole('status');
    expect(announcer).toHaveTextContent(/«Цвет» перемещён на позицию 2 из 2/);
  });

  it('exposes a sr-only keyboard hint linked via aria-describedby (audit 9.2)', () => {
    const { Wrapper } = makeWrapper();
    render(<BindingsList templateId={TEMPLATE_ID} />, { wrapper: Wrapper });
    const list = screen.getByRole('list', { name: 'Список привязок' });
    expect(list.getAttribute('aria-describedby')).toBe(
      'bindings-keyboard-hint',
    );
    const hint = document.getElementById('bindings-keyboard-hint');
    expect(hint).not.toBeNull();
    expect(hint).toHaveTextContent(/Alt со стрелкой/i);
  });

  it('changing the requirement-level select fires a PATCH', async () => {
    const fetchSpy = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ id: 'b1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchSpy);

    const { Wrapper } = makeWrapper();
    render(<BindingsList templateId={TEMPLATE_ID} />, { wrapper: Wrapper });

    const selects = screen.getAllByLabelText('Уровень требования');
    fireEvent.change(selects[0], { target: { value: 'optional' } });

    await waitFor(() =>
      expect(
        fetchSpy.mock.calls.some(([url]) => String(url).endsWith('/b1')),
      ).toBe(true),
    );
    const patchCall = fetchSpy.mock.calls.find(([url]) =>
      String(url).endsWith('/b1'),
    );
    expect(patchCall[1].method).toBe('PATCH');
    expect(JSON.parse(patchCall[1].body)).toEqual({
      requirementLevel: 'optional',
    });
  });
});
