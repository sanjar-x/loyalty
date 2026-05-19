import { proxyToBackend } from '@/shared/api/bff';

const path = ({ templateId }) =>
  `/api/v1/admin/catalog/attribute-templates/${templateId}`;

export const GET = proxyToBackend({ pathFn: path });
export const PATCH = proxyToBackend({ method: 'PATCH', pathFn: path });
export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: path });
