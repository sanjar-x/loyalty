import { proxyToBackend } from '@/shared/api/bff';

const path = ({ attributeId }) =>
  `/api/v1/admin/catalog/attributes/${attributeId}/values`;

export const GET = proxyToBackend({
  pathFn: path,
  allowedParams: ['offset', 'limit', 'isActive', 'valueGroup'],
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: path,
  successStatus: 201,
});
