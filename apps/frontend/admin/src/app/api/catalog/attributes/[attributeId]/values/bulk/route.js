import { proxyToBackend } from '@/shared/api/bff';

// POST /api/catalog/attributes/{aid}/values/bulk
//
// Bulk-add up to 100 values to a single attribute. Used by the
// "Massовый ввод" path in the value modal — admins paste a CSV-ish
// block and the form converts it to BulkAttributeValueItem[].
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ attributeId }) =>
    `/api/v1/admin/catalog/attributes/${attributeId}/values/bulk`,
  successStatus: 201,
});
