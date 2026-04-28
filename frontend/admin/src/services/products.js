import { productsSeed } from '@/data/products';

export function getProducts() {
  return [...productsSeed];
}

// ---------------------------------------------------------------------------
// Product API
// ---------------------------------------------------------------------------

const API_TIMEOUT = 30_000;

const API_ERROR_RU = {
  'Cannot delete a published product. Archive it first.':
    'Нельзя удалить опубликованный товар. Сначала переместите в архив.',
  'Product not found': 'Товар не найден',
  'Product is already in the requested status':
    'Товар уже находится в запрашиваемом статусе',
  'Invalid status transition': 'Недопустимый переход статуса',
  'Not authenticated': 'Сессия истекла. Войдите заново.',
  'Backend service unreachable': 'Сервер недоступен. Попробуйте позже.',
  'Backend unavailable': 'Сервер недоступен. Попробуйте позже.',
  'Invalid product ID': 'Некорректный ID товара',
  'Service unavailable': 'Сервис временно недоступен',
  'Image service unreachable': 'Сервис изображений недоступен',
};

function translateApiMessage(msg) {
  if (!msg) return null;
  return API_ERROR_RU[msg] ?? null;
}

async function api(url, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const res = await fetch(url, {
      credentials: 'include',
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.status === 429) {
      const retryAfter = parseInt(res.headers.get('Retry-After') || '5', 10);
      const error = new Error(
        `Слишком много запросов. Повторите через ${retryAfter} сек.`,
      );
      error.code = 'RATE_LIMITED';
      error.status = 429;
      error.retryAfter = retryAfter;
      throw error;
    }

    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const err = data?.error ?? data?.detail ?? {};
      const raw = err.message ?? `Ошибка сервера (${res.status})`;
      const error = new Error(translateApiMessage(raw) ?? raw);
      error.code = err.code ?? 'UNKNOWN';
      error.status = res.status;
      error.details = err.details ?? {};
      throw error;
    }
    return data;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      const error = new Error(
        'Запрос превысил время ожидания. Проверьте соединение и попробуйте снова.',
      );
      error.code = 'TIMEOUT';
      throw error;
    }
    throw err;
  }
}

function jsonOpts(body) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

/**
 * Fetch paginated product list from the backend via BFF.
 * @param {Object} params
 * @param {number} [params.offset=0]
 * @param {number} [params.limit=50]
 * @param {string} [params.status] - draft | enriching | ready_for_review | published | archived
 * @param {string} [params.brandId] - UUID
 * @param {string} [params.sortBy] - newest | oldest | popularity | name_asc | name_desc
 * @returns {Promise<{items: Object[], total: number, offset: number, limit: number, hasNext: boolean}>}
 */
export async function fetchProducts({ offset = 0, limit = 50, status, brandId, sortBy } = {}) {
  const params = new URLSearchParams();
  params.set('offset', String(offset));
  params.set('limit', String(limit));
  if (status) params.set('status', status);
  if (brandId) params.set('brand_id', brandId);
  if (sortBy) params.set('sort_by', sortBy);

  return api(`/api/catalog/products?${params.toString()}`);
}

export async function fetchProductCounts() {
  return api('/api/catalog/products/counts');
}

export async function createProduct(payload) {
  return api('/api/catalog/products', jsonOpts(payload));
}

export async function createVariant(productId, payload) {
  return api(`/api/catalog/products/${productId}/variants`, jsonOpts(payload));
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

export async function deleteMedia(storageObjectId) {
  return api(`/api/media/${storageObjectId}`, { method: 'DELETE' });
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
      eventSource.onerror = null;
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

export async function fetchImageAsFile(imageUrl) {
  const res = await fetch(`/api/media/proxy?url=${encodeURIComponent(imageUrl)}`, {
    credentials: 'include',
  });
  if (!res.ok) {
    const error = new Error('Не удалось загрузить изображение');
    error.code = 'IMAGE_FETCH_FAILED';
    throw error;
  }
  const blob = await res.blob();
  const ext = blob.type.split('/')[1] || 'jpg';
  return new File([blob], `image.${ext}`, { type: blob.type });
}

export async function associateMedia(productId, payload) {
  // payload = { storageObjectId, url, variantId, role, sortOrder, mediaType, isExternal }
  // `url` is the public URL from ImageBackend (SSE metadata.url) or S3 raw URL fallback.
  // Passing it explicitly ensures GET /media returns a populated url field instead of null.
  return api(`/api/catalog/products/${productId}/media`, jsonOpts(payload));
}

export async function changeProductStatus(productId, status) {
  return api(`/api/catalog/products/${productId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
}

export async function deleteProduct(productId) {
  return api(`/api/catalog/products/${productId}`, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// Edit-mode API functions
// ---------------------------------------------------------------------------

export async function listProductMedia(productId) {
  return api(`/api/catalog/products/${productId}/media`);
}

export async function updateVariant(productId, variantId, payload) {
  return api(`/api/catalog/products/${productId}/variants/${variantId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function deleteVariant(productId, variantId) {
  return api(`/api/catalog/products/${productId}/variants/${variantId}`, {
    method: 'DELETE',
  });
}

export async function updateMediaAsset(productId, mediaId, payload) {
  return api(`/api/catalog/products/${productId}/media/${mediaId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function deleteMediaAsset(productId, mediaId) {
  return api(`/api/catalog/products/${productId}/media/${mediaId}`, {
    method: 'DELETE',
  });
}

export async function reorderMedia(productId, payload) {
  return api(`/api/catalog/products/${productId}/media/reorder`, jsonOpts(payload));
}

export async function deleteProductAttribute(productId, attributeId) {
  return api(`/api/catalog/products/${productId}/attributes/${attributeId}`, {
    method: 'DELETE',
  });
}
