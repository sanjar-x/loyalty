import { proxyToBackend } from '@/shared/api/bff';

// GET / PUT / DELETE a single logistics provider account.
// Backend: /api/v1/admin/logistics/provider-accounts/{accountId}.
const accountPath = (params) =>
  `/api/v1/admin/logistics/provider-accounts/${params.providerId}`;

export const GET = proxyToBackend({ pathFn: accountPath });

export const PUT = proxyToBackend({ method: 'PUT', pathFn: accountPath });

export const DELETE = proxyToBackend({ method: 'DELETE', pathFn: accountPath });
