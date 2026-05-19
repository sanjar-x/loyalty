import { proxyToBackend } from '@/shared/api/bff';

const path = ({ templateId, bindingId }) =>
  `/api/v1/admin/catalog/attribute-templates/${templateId}/attributes/${bindingId}`;

export const PATCH = proxyToBackend({ method: 'PATCH', pathFn: path });
export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: path });
