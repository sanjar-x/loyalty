import { proxyToBackend } from '@/shared/api/bff';

const path = ({ roleId }) => `/api/v1/admin/roles/${roleId}`;

export const GET = proxyToBackend({ pathFn: path });
export const PATCH = proxyToBackend({ method: 'PATCH', pathFn: path });
export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: path });
