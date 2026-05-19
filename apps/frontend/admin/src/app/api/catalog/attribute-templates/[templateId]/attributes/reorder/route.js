import { proxyToBackend } from '@/shared/api/bff';

// POST /api/catalog/attribute-templates/{templateId}/attributes/reorder
//
// Body matches `TemplateBindingReorderRequest` — up to 500 items,
// each `{bindingId, sortOrder}`. Used by the BindingsList DnD wire;
// the same ergonomics as `media/reorder` in catalog products.
export const POST = proxyToBackend({
  method: 'POST',
  pathFn: ({ templateId }) =>
    `/api/v1/admin/catalog/attribute-templates/${templateId}/attributes/reorder`,
});
