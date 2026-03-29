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

export async function reserveMediaUpload(payload) {
  // payload = { contentType, filename }
  return api('/api/media/upload', jsonOpts(payload));
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

export async function confirmMedia(storageObjectId) {
  return api(`/api/media/${storageObjectId}/confirm`, { method: 'POST' });
}

const POLL_INTERVALS = [500, 1000, 2000];

export async function pollMediaStatus(storageObjectId, { maxWait = 60000 } = {}) {
  const start = Date.now();
  let attempt = 0;

  while (Date.now() - start < maxWait) {
    const data = await api(`/api/media/${storageObjectId}`);

    if (data.status === 'COMPLETED') return data;

    if (data.status === 'FAILED') {
      const error = new Error('Media processing failed');
      error.code = 'MEDIA_PROCESSING_FAILED';
      throw error;
    }

    const delay = POLL_INTERVALS[Math.min(attempt, POLL_INTERVALS.length - 1)];
    await new Promise((r) => setTimeout(r, delay));
    attempt++;
  }

  const error = new Error('Media processing timed out');
  error.code = 'MEDIA_PROCESSING_TIMEOUT';
  throw error;
}

export async function addExternalMedia(payload) {
  // payload = { url }
  return api('/api/media/external', jsonOpts(payload));
}

export async function changeProductStatus(productId, status) {
  return api(`/api/catalog/products/${productId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
}
