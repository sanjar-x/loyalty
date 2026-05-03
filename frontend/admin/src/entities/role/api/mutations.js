'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createRole,
  deleteRole,
  setRolePermissions,
  updateRole,
} from './roles';
import { roleKeys } from './keys';

export function useCreateRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createRole,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: roleKeys.lists() });
    },
  });
}

export function useUpdateRole(roleId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updateRole(roleId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: roleKeys.detail(roleId) });
      qc.invalidateQueries({ queryKey: roleKeys.lists() });
    },
  });
}

export function useDeleteRole(roleId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => deleteRole(roleId),
    onSuccess: () => {
      qc.removeQueries({ queryKey: roleKeys.detail(roleId) });
      qc.invalidateQueries({ queryKey: roleKeys.lists() });
    },
  });
}

export function useSetRolePermissions(roleId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (permissionIds) => setRolePermissions(roleId, permissionIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: roleKeys.detail(roleId) });
      qc.invalidateQueries({ queryKey: roleKeys.lists() });
    },
  });
}
