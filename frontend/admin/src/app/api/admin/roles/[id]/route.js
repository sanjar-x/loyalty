import { proxyToBackend } from '@/shared/api/bff';

const path = ({ id }) => `/api/v1/admin/roles/${id}`;

export const GET = proxyToBackend({ pathFn: path });
export const PATCH = proxyToBackend({ method: 'PATCH', pathFn: path });
export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: path });
