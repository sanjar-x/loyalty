import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: (_params, search) => {
    const offset = search.get('offset') ?? '0';
    const limit = search.get('limit') ?? '200';
    return `/api/v1/admin/suppliers?offset=${offset}&limit=${limit}`;
  },
  forwardSearch: false,
});

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/suppliers',
  successStatus: 201,
});
