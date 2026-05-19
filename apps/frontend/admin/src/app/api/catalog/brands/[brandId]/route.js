import { proxyToBackend } from '@/shared/api/bff';

const path = ({ brandId }) => `/api/v1/admin/catalog/brands/${brandId}`;

export const GET = proxyToBackend({ pathFn: path });
export const PATCH = proxyToBackend({ method: 'PATCH', pathFn: path });
export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: path });
