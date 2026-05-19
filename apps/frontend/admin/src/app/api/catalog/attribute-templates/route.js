import { proxyToBackend } from '@/shared/api/bff';

const TEMPLATES_PATH = '/api/v1/admin/catalog/attribute-templates';

export const GET = proxyToBackend({
  pathFn: () => TEMPLATES_PATH,
  allowedParams: ['offset', 'limit'],
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => TEMPLATES_PATH,
  successStatus: 201,
});
