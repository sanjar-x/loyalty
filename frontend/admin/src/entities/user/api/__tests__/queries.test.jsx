import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWrapper } from '@/shared/query';
import * as identitiesApi from '../identities';
import { identityKeys } from '../keys';
import { useIdentities, useIdentity } from '../queries';

describe('identity queries', () => {
  beforeEach(() => {
    vi.spyOn(identitiesApi, 'fetchIdentities');
    vi.spyOn(identitiesApi, 'fetchIdentity');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useIdentities', () => {
    it('returns the normalized list and respects keepPreviousData on filter swap', async () => {
      identitiesApi.fetchIdentities
        .mockResolvedValueOnce({
          items: [{ id: '1', email: 'a@example.com' }],
          total: 1,
        })
        .mockResolvedValueOnce({
          items: [{ id: '2', email: 'b@example.com' }],
          total: 1,
        });

      const { Wrapper, client } = createWrapper();
      const initialFilters = { search: '', page: 1 };
      const { result, rerender } = renderHook(
        ({ filters }) => useIdentities(filters),
        { wrapper: Wrapper, initialProps: { filters: initialFilters } },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.items?.[0]?.email).toBe('a@example.com');
      expect(client.getQueryData(identityKeys.list(initialFilters))).toEqual({
        items: [{ id: '1', email: 'a@example.com' }],
        total: 1,
      });

      const nextFilters = { search: 'b', page: 1 };
      rerender({ filters: nextFilters });

      // Previous data is held while the new query is loading.
      expect(result.current.data?.items?.[0]?.email).toBe('a@example.com');

      await waitFor(() =>
        expect(result.current.data?.items?.[0]?.email).toBe('b@example.com'),
      );
      expect(identitiesApi.fetchIdentities).toHaveBeenCalledTimes(2);
    });
  });

  describe('useIdentity', () => {
    it('does not fetch until identityId is provided', () => {
      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useIdentity(null), {
        wrapper: Wrapper,
      });
      expect(result.current.fetchStatus).toBe('idle');
      expect(identitiesApi.fetchIdentity).not.toHaveBeenCalled();
    });

    it('returns the identity detail when an id is provided', async () => {
      identitiesApi.fetchIdentity.mockResolvedValueOnce({
        id: 'u1',
        email: 'admin@example.com',
        roles: [],
      });

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => useIdentity('u1'), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.email).toBe('admin@example.com');
      expect(client.getQueryData(identityKeys.detail('u1'))).toBeDefined();
      expect(identitiesApi.fetchIdentity).toHaveBeenCalledWith('u1');
    });
  });
});
