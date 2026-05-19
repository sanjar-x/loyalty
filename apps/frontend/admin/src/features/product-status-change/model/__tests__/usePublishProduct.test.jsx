import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import { pathToPublished } from '../../lib/pathToPublished';
import { usePublishProduct } from '../usePublishProduct';

vi.mock('@/entities/product', async (orig) => {
  const actual = await orig();
  return {
    ...actual,
    changeProductStatus: vi.fn(),
  };
});

import { changeProductStatus, productKeys } from '@/entities/product';

describe('pathToPublished', () => {
  it('walks the full ladder from draft', () => {
    expect(pathToPublished('draft')).toEqual([
      'enriching',
      'ready_for_review',
      'published',
    ]);
  });

  it('returns the remaining slice from an intermediate status', () => {
    expect(pathToPublished('enriching')).toEqual([
      'ready_for_review',
      'published',
    ]);
    expect(pathToPublished('ready_for_review')).toEqual(['published']);
  });

  it('returns empty array when already published (no-op)', () => {
    expect(pathToPublished('published')).toEqual([]);
  });

  it('throws for non-publish-ladder statuses', () => {
    expect(() => pathToPublished('archived')).toThrow(/нельзя опубликовать/);
    expect(() => pathToPublished('bogus')).toThrow();
  });
});

describe('usePublishProduct', () => {
  let qc;
  function wrapper({ children }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }

  beforeEach(() => {
    qc = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    changeProductStatus.mockReset();
  });

  afterEach(() => {
    qc.clear();
  });

  it('chains every step from draft → published', async () => {
    qc.setQueryData(productKeys.detail('p-1'), { status: 'draft' });
    changeProductStatus.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => usePublishProduct('p-1'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(changeProductStatus).toHaveBeenCalledTimes(3);
    expect(changeProductStatus.mock.calls.map((c) => c[1])).toEqual([
      'enriching',
      'ready_for_review',
      'published',
    ]);
  });

  it('skips intermediate steps when already at ready_for_review', async () => {
    qc.setQueryData(productKeys.detail('p-2'), { status: 'ready_for_review' });
    changeProductStatus.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => usePublishProduct('p-2'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(changeProductStatus).toHaveBeenCalledTimes(1);
    expect(changeProductStatus).toHaveBeenCalledWith('p-2', 'published');
  });

  it('is a no-op when product is already published', async () => {
    qc.setQueryData(productKeys.detail('p-3'), { status: 'published' });

    const { result } = renderHook(() => usePublishProduct('p-3'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(changeProductStatus).not.toHaveBeenCalled();
    expect(result.current.data).toEqual({ ok: true, alreadyPublished: true });
  });

  it('stops the chain on first error and propagates it', async () => {
    qc.setQueryData(productKeys.detail('p-4'), { status: 'draft' });
    changeProductStatus
      .mockResolvedValueOnce({ ok: true })
      .mockRejectedValueOnce(
        Object.assign(new Error('boom'), {
          code: 'PRODUCT_NOT_READY',
          details: { skuDiagnostics: [] },
        }),
      );

    const { result } = renderHook(() => usePublishProduct('p-4'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isError).toBe(true));

    // Made it past enriching, blew up on ready_for_review — never tried published.
    expect(changeProductStatus).toHaveBeenCalledTimes(2);
    expect(result.current.error?.code).toBe('PRODUCT_NOT_READY');
  });

  it('falls back to draft path when query cache has no entry', async () => {
    // `getQueryData` returns undefined → defaults to draft
    changeProductStatus.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => usePublishProduct('p-5'), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(changeProductStatus).toHaveBeenCalledTimes(3);
  });
});
