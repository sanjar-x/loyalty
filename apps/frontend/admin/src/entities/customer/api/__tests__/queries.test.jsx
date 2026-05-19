import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '@/shared/api/clientFetch';
import { createWrapper } from '@/shared/query';
import * as customersApi from '../customers';
import { customerKeys } from '../keys';
import { useCustomer, useCustomers } from '../queries';

/**
 * FA-402 — customer queries regression guard.
 *
 * Customer list/detail share the same TanStack Query plumbing as identity
 * list/detail but live in a separate cache namespace (`customerKeys`) — the
 * fork happened so admin customer screens don't share cache with the wider
 * identity (staff + customer) endpoint. These tests fixate that boundary
 * and the response-shape normalization done inside `fetchCustomers`.
 */
describe('customer queries', () => {
  beforeEach(() => {
    vi.spyOn(customersApi, 'fetchCustomers');
    vi.spyOn(customersApi, 'fetchCustomer');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useCustomers', () => {
    it('returns the normalized list and respects keepPreviousData on filter swap', async () => {
      customersApi.fetchCustomers
        .mockResolvedValueOnce({
          items: [{ id: 'c1', email: 'one@example.com' }],
          total: 1,
          offset: 0,
          limit: 20,
        })
        .mockResolvedValueOnce({
          items: [{ id: 'c2', email: 'two@example.com' }],
          total: 1,
          offset: 0,
          limit: 20,
        });

      const { Wrapper, client } = createWrapper();
      const initialFilters = { search: '', page: 1 };
      const { result, rerender } = renderHook(
        ({ filters }) => useCustomers(filters),
        { wrapper: Wrapper, initialProps: { filters: initialFilters } },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.items?.[0]?.email).toBe('one@example.com');
      expect(client.getQueryData(customerKeys.list(initialFilters))).toEqual({
        items: [{ id: 'c1', email: 'one@example.com' }],
        total: 1,
        offset: 0,
        limit: 20,
      });

      const nextFilters = { search: 'two', page: 1 };
      rerender({ filters: nextFilters });

      // Previous data is held while the new query is loading.
      expect(result.current.data?.items?.[0]?.email).toBe('one@example.com');

      await waitFor(() =>
        expect(result.current.data?.items?.[0]?.email).toBe('two@example.com'),
      );
      expect(customersApi.fetchCustomers).toHaveBeenCalledTimes(2);
    });

    it('keeps the customer cache namespace isolated from other identity caches', async () => {
      customersApi.fetchCustomers.mockResolvedValueOnce({
        items: [{ id: 'c1' }],
        total: 1,
      });

      const { Wrapper, client } = createWrapper();
      const filters = { search: '', page: 1 };
      const { result } = renderHook(() => useCustomers(filters), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(client.getQueryData(customerKeys.list(filters))).toBeDefined();
      // Sanity check: the identity namespace must be unused by a customer
      // query (the cache keys are intentionally disjoint).
      expect(
        client.getQueryData(['identities', 'list', filters]),
      ).toBeUndefined();
    });
  });

  describe('useCustomer', () => {
    it('does not fetch until identityId is provided', () => {
      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useCustomer(null), {
        wrapper: Wrapper,
      });
      expect(result.current.fetchStatus).toBe('idle');
      expect(customersApi.fetchCustomer).not.toHaveBeenCalled();
    });

    it('returns the customer detail when an identityId is provided', async () => {
      customersApi.fetchCustomer.mockResolvedValueOnce({
        id: 'c1',
        email: 'customer@example.com',
        firstName: 'Анна',
        lastName: 'Иванова',
        isActive: true,
        roles: [{ id: 'r1', name: 'customer' }],
      });

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => useCustomer('c1'), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.email).toBe('customer@example.com');
      expect(client.getQueryData(customerKeys.detail('c1'))).toBeDefined();
      expect(customersApi.fetchCustomer).toHaveBeenCalledWith('c1');
    });
  });
});

describe('fetchCustomers (response shape regression guard)', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'get');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('builds the query with offset, limit, sortBy and sortOrder', async () => {
    apiClient.get.mockResolvedValueOnce({ items: [], total: 0 });
    await customersApi.fetchCustomers({
      page: 2,
      limit: 10,
      sort: 'email:asc',
    });
    const url = apiClient.get.mock.calls[0][0];
    expect(url).toContain('offset=10');
    expect(url).toContain('limit=10');
    expect(url).toContain('sortBy=email');
    expect(url).toContain('sortOrder=asc');
  });

  it('omits search when blank or whitespace-only', async () => {
    apiClient.get.mockResolvedValueOnce({ items: [], total: 0 });
    await customersApi.fetchCustomers({ search: '   ' });
    expect(apiClient.get.mock.calls[0][0]).not.toContain('search=');
  });

  it('includes isActive when explicitly set to false (boolean), not just truthy', async () => {
    apiClient.get.mockResolvedValueOnce({ items: [], total: 0 });
    await customersApi.fetchCustomers({ isActive: false });
    expect(apiClient.get.mock.calls[0][0]).toContain('isActive=false');
  });

  it('omits isActive when undefined, null or empty string', async () => {
    apiClient.get.mockResolvedValueOnce({ items: [], total: 0 });
    await customersApi.fetchCustomers({ isActive: '' });
    expect(apiClient.get.mock.calls[0][0]).not.toContain('isActive=');
  });

  it('falls back to an empty items array when the backend omits it', async () => {
    apiClient.get.mockResolvedValueOnce({ total: 5 });
    const result = await customersApi.fetchCustomers();
    expect(result.items).toEqual([]);
    expect(result.total).toBe(5);
  });

  it('falls back to numeric defaults when total/offset/limit are non-numeric', async () => {
    apiClient.get.mockResolvedValueOnce({
      items: [{ id: 'c1' }],
      total: 'not-a-number',
      offset: null,
      limit: undefined,
    });
    const result = await customersApi.fetchCustomers();
    expect(result.total).toBe(0);
    expect(result.offset).toBe(0);
    expect(result.limit).toBe(20);
  });
});
