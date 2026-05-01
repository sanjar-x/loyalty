'use client';

import { useQuery } from '@tanstack/react-query';
import {
  REFERENCE_DATA_STALE_TIME_MS,
  SESSION_STATIC_STALE_TIME_MS,
} from '@/shared/query';
import { fetchPermissions, fetchRole, fetchRoles } from './roles';
import { permissionKeys, roleKeys } from './keys';

/**
 * Roles list — small, slowly changing reference data.
 */
export function useRoles() {
  return useQuery({
    queryKey: roleKeys.lists(),
    queryFn: fetchRoles,
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}

/**
 * Single role detail (includes assigned permissions).
 * Disabled until roleId is provided.
 */
export function useRole(roleId) {
  return useQuery({
    queryKey: roleKeys.detail(roleId),
    queryFn: () => fetchRole(roleId),
    enabled: Boolean(roleId),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
  });
}

/**
 * Permission catalogue — effectively static within a release.
 */
export function usePermissions() {
  return useQuery({
    queryKey: permissionKeys.lists(),
    queryFn: fetchPermissions,
    staleTime: SESSION_STATIC_STALE_TIME_MS,
  });
}
