import { productsSeed } from '@/data/products';

export function getProducts() {
  return [...productsSeed];
}

// ---------------------------------------------------------------------------
// Product API
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

export async function getProduct(productId) {
  return api(`/api/catalog/products/${productId}`);
}

export async function getProductCompleteness(productId) {
  return api(`/api/catalog/products/${productId}/completeness`);
}

export async function updateProduct(productId, payload) {
  return api(`/api/catalog/products/${productId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
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
  // Upload through BFF proxy to avoid CSP connect-src restrictions.
  // The presigned URL points to an external S3 domain that the browser cannot reach directly.
  const formData = new FormData();
  formData.append('file', file);
  formData.append('presignedUrl', presignedUrl);

  const res = await fetch('/api/media/s3-upload', {
    method: 'POST',
    body: formData,
    credentials: 'include',
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const error = new Error(data?.error?.message || 'File upload to S3 failed');
    error.code = 'S3_UPLOAD_FAILED';
    error.status = res.status;
    throw error;
  }
}

export async function confirmMedia(storageObjectId) {
  return api(`/api/media/${storageObjectId}/confirm`, { method: 'POST' });
}

const S3_ORIGIN = 'https://t3.storage.dev/loyality';
const PUBLIC_ORIGIN = 'https://loyality.t3.tigrisfiles.io';

export function extractRawUrl(presignedUrl) {
  const [urlWithoutQuery] = presignedUrl.split('?');
  return urlWithoutQuery.replace(S3_ORIGIN, PUBLIC_ORIGIN);
}

export function subscribeMediaStatus(storageObjectId, { timeout = 120_000, signal } = {}) {
  return new Promise((resolve, reject) => {
    const url = `/api/media/${storageObjectId}/status`;
    const eventSource = new EventSource(url);
    let settled = false;

    const timeoutId = setTimeout(() => {
      if (settled) return;
      settled = true;
      eventSource.close();
      const err = new Error('Media processing timed out');
      err.code = 'MEDIA_PROCESSING_TIMEOUT';
      reject(err);
    }, timeout);

    function cleanup() {
      clearTimeout(timeoutId);
      eventSource.close();
    }

    if (signal) {
      signal.addEventListener('abort', () => {
        if (settled) return;
        settled = true;
        cleanup();
        reject(new DOMException('Aborted', 'AbortError'));
      });
    }

    eventSource.addEventListener('status', (event) => {
      if (settled) return;

      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      const status = (data.status || '').toUpperCase();

      if (status === 'COMPLETED') {
        settled = true;
        cleanup();
        resolve({
          status: 'COMPLETED',
          url: data.url,
          variants: data.variants || [],
          storageObjectId: data.storageObjectId || data.storage_object_id,
        });
      } else if (status === 'FAILED') {
        settled = true;
        cleanup();
        const err = new Error(data.error || 'Media processing failed');
        err.code = 'MEDIA_PROCESSING_FAILED';
        reject(err);
      }
    });

    eventSource.onerror = () => {
      if (settled) return;
      settled = true;
      cleanup();
      const err = new Error('SSE connection lost');
      err.code = 'SSE_CONNECTION_ERROR';
      reject(err);
    };
  });
}

export async function addExternalMedia(payload) {
  // payload = { url }
  return api('/api/media/external', jsonOpts(payload));
}

export async function associateMedia(productId, payload) {
  // payload = { storageObjectId, variantId, role, sortOrder, mediaType, isExternal }
  return api(`/api/catalog/products/${productId}/media`, jsonOpts(payload));
}

export async function changeProductStatus(productId, status) {
  return api(`/api/catalog/products/${productId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
}
