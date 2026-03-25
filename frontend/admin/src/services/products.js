import { productsSeed } from '@/data/products';

export function getProducts() {
  return [...productsSeed];
}

// ---------------------------------------------------------------------------
// Product creation API
// ---------------------------------------------------------------------------

async function api(url, options = {}) {
  const res = await fetch(url, { credentials: 'include', ...options });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error ?? data?.detail ?? {};
    const error = new Error(err.message ?? `API error ${res.status}`);
    error.code = err.code ?? 'UNKNOWN';
    error.status = res.status;
    error.details = err.details ?? {};
    throw error;
  }
  return data;
}

function jsonOpts(body) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export async function createProduct(payload) {
  return api('/api/catalog/products', jsonOpts(payload));
}

export async function bulkAssignAttrs(productId, payload) {
  return api(`/api/catalog/products/${productId}/attributes/bulk`, jsonOpts(payload));
}

export async function generateSkus(productId, variantId, payload) {
  return api(
    `/api/catalog/products/${productId}/variants/${variantId}/skus/generate`,
    jsonOpts(payload),
  );
}

export async function listSkus(productId, variantId) {
  return api(`/api/catalog/products/${productId}/variants/${variantId}/skus`);
}

export async function updateSku(productId, variantId, skuId, payload) {
  return api(
    `/api/catalog/products/${productId}/variants/${variantId}/skus/${skuId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  );
}

export async function reserveMediaUpload(productId, payload) {
  return api(`/api/catalog/products/${productId}/media/upload`, jsonOpts(payload));
}

export async function uploadToS3(presignedUrl, file) {
  const res = await fetch(presignedUrl, {
    method: 'PUT',
    body: file,
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
  });
  if (!res.ok) {
    const error = new Error('File upload to S3 failed');
    error.code = 'S3_UPLOAD_FAILED';
    error.status = res.status;
    throw error;
  }
}

export async function confirmMedia(productId, mediaId) {
  return api(`/api/catalog/products/${productId}/media/${mediaId}/confirm`, { method: 'POST' });
}

export async function addExternalMedia(productId, payload) {
  return api(`/api/catalog/products/${productId}/media/external`, jsonOpts(payload));
}

export async function changeProductStatus(productId, status) {
  return api(`/api/catalog/products/${productId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
}
