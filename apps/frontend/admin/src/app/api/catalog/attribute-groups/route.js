import { proxyToBackend } from '@/shared/api/bff';

const ATTRIBUTE_GROUPS_PATH = '/api/v1/admin/catalog/attribute-groups';

export const GET = proxyToBackend({
  pathFn: () => ATTRIBUTE_GROUPS_PATH,
  allowedParams: ['offset', 'limit'],
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => ATTRIBUTE_GROUPS_PATH,
  successStatus: 201,
});
