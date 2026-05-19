import { proxyToBackend } from '@/shared/api/bff';

export const GET = proxyToBackend({
  pathFn: ({ customerId }) => `/api/v1/admin/customers/${customerId}`,
});
