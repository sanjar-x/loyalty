import { proxyToBackend } from '@/shared/api/bff';

// GET  /api/catalog/attributes              → /api/v1/admin/catalog/attributes
// POST /api/catalog/attributes              → /api/v1/admin/catalog/attributes
//
// List supports `offset`, `limit`, `level`, `groupId`, `isDictionary`
// — backend validates each individually and ignores unknown keys, but
// keeping the allow-list explicit makes the BFF surface auditable.
export const GET = proxyToBackend({
  pathFn: () => '/api/v1/admin/catalog/attributes',
  allowedParams: [
    'offset',
    'limit',
    'level',
    'groupId',
    'isDictionary',
    'isFilterable',
    'isSearchable',
  ],
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/catalog/attributes',
  successStatus: 201,
});
