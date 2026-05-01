import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWrapper } from '@/shared/query';
import * as productsApi from '../products';
import { productKeys } from '../keys';
import {
  useProduct,
  useProductCompleteness,
  useProductCounts,
  useProductMedia,
} from '../queries';

describe('product detail queries', () => {
  beforeEach(() => {
    vi.spyOn(productsApi, 'getProduct');
    vi.spyOn(productsApi, 'getProductCompleteness');
    vi.spyOn(productsApi, 'listProductMedia');
    vi.spyOn(productsApi, 'fetchProductCounts');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useProduct', () => {
    it('does not fetch when productId is missing', () => {
      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useProduct(undefined), {
        wrapper: Wrapper,
      });
      expect(result.current.fetchStatus).toBe('idle');
      expect(productsApi.getProduct).not.toHaveBeenCalled();
    });

    it('fetches and caches the product detail', async () => {
      productsApi.getProduct.mockResolvedValueOnce({
        id: 'p1',
        titleI18N: { ru: 'Тест' },
        status: 'draft',
      });

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => useProduct('p1'), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.id).toBe('p1');
      expect(client.getQueryData(productKeys.detail('p1'))).toMatchObject({
        id: 'p1',
        status: 'draft',
      });
    });
  });

  describe('useProductCompleteness', () => {
    it('caches under a key nested below the product detail', async () => {
      productsApi.getProductCompleteness.mockResolvedValueOnce({
        filledRequired: 3,
        missingRequired: 1,
      });

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => useProductCompleteness('p1'), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.missingRequired).toBe(1);
      expect(client.getQueryData(productKeys.completeness('p1'))).toBeDefined();
    });
  });

  describe('useProductMedia', () => {
    it('returns the media list', async () => {
      productsApi.listProductMedia.mockResolvedValueOnce({
        items: [{ id: 'm1', url: 'https://example.com/x.jpg' }],
      });

      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useProductMedia('p1'), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.items).toHaveLength(1);
    });
  });

  describe('useProductCounts', () => {
    it('fetches FSM tab counts', async () => {
      productsApi.fetchProductCounts.mockResolvedValueOnce({
        draft: 1,
        published: 5,
      });

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => useProductCounts(), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual({ draft: 1, published: 5 });
      expect(client.getQueryData(productKeys.counts())).toEqual({
        draft: 1,
        published: 5,
      });
    });
  });
});
