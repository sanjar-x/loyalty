import { proxyToBackend } from '@/shared/api/bff';

const path = ({ templateId }) =>
  `/api/v1/admin/catalog/attribute-templates/${templateId}/attributes`;

export const GET = proxyToBackend({
  pathFn: path,
  allowedParams: ['offset', 'limit'],
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: path,
  successStatus: 201,
});
