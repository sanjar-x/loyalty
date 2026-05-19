import { proxyToBackend } from '@/shared/api/bff';

const path = ({ attributeId, valueId }) =>
  `/api/v1/admin/catalog/attributes/${attributeId}/values/${valueId}`;

export const GET = proxyToBackend({ pathFn: path });
export const PATCH = proxyToBackend({ method: 'PATCH', pathFn: path });
export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: path });
