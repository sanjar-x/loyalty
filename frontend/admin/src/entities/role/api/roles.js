import { apiClient } from '@/shared/api/client-fetch';

export const fetchRoles = () => apiClient.get('/api/admin/roles');

export const fetchRole = (roleId) =>
  apiClient.get(`/api/admin/roles/${roleId}`);

export const fetchPermissions = () => apiClient.get('/api/admin/permissions');

export const createRole = (payload) =>
  apiClient.post('/api/admin/roles', payload);

export const updateRole = (roleId, payload) =>
  apiClient.patch(`/api/admin/roles/${roleId}`, payload);

export const deleteRole = (roleId) =>
  apiClient.del(`/api/admin/roles/${roleId}`);

export const setRolePermissions = (roleId, permissionIds) =>
  apiClient.put(`/api/admin/roles/${roleId}/permissions`, { permissionIds });
