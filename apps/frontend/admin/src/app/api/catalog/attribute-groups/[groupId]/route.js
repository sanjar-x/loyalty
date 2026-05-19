import { proxyToBackend } from '@/shared/api/bff';

const path = ({ groupId }) =>
  `/api/v1/admin/catalog/attribute-groups/${groupId}`;

export const GET = proxyToBackend({ pathFn: path });
export const PATCH = proxyToBackend({ method: 'PATCH', pathFn: path });
export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: path });
