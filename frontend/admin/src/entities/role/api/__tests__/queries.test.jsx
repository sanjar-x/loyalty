import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWrapper } from '@/shared/query';
import * as rolesApi from '../roles';
import { permissionKeys, roleKeys } from '../keys';
import { usePermissions, useRole, useRoles } from '../queries';

describe('role queries', () => {
  beforeEach(() => {
    vi.spyOn(rolesApi, 'fetchRoles');
    vi.spyOn(rolesApi, 'fetchRole');
    vi.spyOn(rolesApi, 'fetchPermissions');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useRoles', () => {
    it('returns roles list under the canonical key', async () => {
      rolesApi.fetchRoles.mockResolvedValueOnce([
        { id: '1', name: 'admin' },
        { id: '2', name: 'manager' },
      ]);

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => useRoles(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual([
        { id: '1', name: 'admin' },
        { id: '2', name: 'manager' },
      ]);
      expect(client.getQueryData(roleKeys.lists())).toHaveLength(2);
      expect(rolesApi.fetchRoles).toHaveBeenCalledTimes(1);
    });
  });

  describe('useRole', () => {
    it('does not fetch when roleId is missing', () => {
      const { Wrapper } = createWrapper();
      const { result } = renderHook(() => useRole(undefined), {
        wrapper: Wrapper,
      });
      expect(result.current.fetchStatus).toBe('idle');
      expect(rolesApi.fetchRole).not.toHaveBeenCalled();
    });

    it('fetches the role detail when roleId is provided', async () => {
      rolesApi.fetchRole.mockResolvedValueOnce({
        id: 'r1',
        name: 'admin',
        permissions: [{ id: 'p1' }],
      });

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => useRole('r1'), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toMatchObject({
        id: 'r1',
        permissions: [{ id: 'p1' }],
      });
      expect(client.getQueryData(roleKeys.detail('r1'))).toBeDefined();
      expect(rolesApi.fetchRole).toHaveBeenCalledWith('r1');
    });
  });

  describe('usePermissions', () => {
    it('returns the permission catalogue', async () => {
      rolesApi.fetchPermissions.mockResolvedValueOnce([
        { resource: 'orders', permissions: [{ id: 'p1', action: 'read' }] },
      ]);

      const { Wrapper, client } = createWrapper();
      const { result } = renderHook(() => usePermissions(), {
        wrapper: Wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.[0]?.resource).toBe('orders');
      expect(client.getQueryData(permissionKeys.lists())).toHaveLength(1);
    });
  });
});
