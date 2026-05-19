import { proxyToBackend } from '@/shared/api/bff';

// POST /api/catalog/attribute-templates/clone
//
// Body matches `CloneAttributeTemplateRequest` —
// `{sourceTemplateId, newCode, newNameI18N, newDescriptionI18N?}`. Backend
// duplicates the template + every binding atomically and returns the
// new template id; we just forward the body.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: () => '/api/v1/admin/catalog/attribute-templates/clone',
  successStatus: 201,
});
