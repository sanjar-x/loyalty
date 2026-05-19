import { proxyToBackend } from '@/shared/api/bff';

export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ customerId }) =>
    `/api/v1/admin/customers/${customerId}/reactivate`,
  forwardBody: false,
});
