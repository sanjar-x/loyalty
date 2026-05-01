import { apiClient, ApiError } from '@/shared/api/client-fetch';
import { productsSeed } from '@/shared/mocks/products';

// Mock-only seed accessor for legacy callers; backed by the products list page
// that still relies on local fixtures while the catalogue is in flight.
export function getProducts() {
  return [...productsSeed];
}

const PRODUCT_ERROR_TRANSLATIONS = {
  'Cannot delete a published product. Archive it first.':
    'Нельзя удалить опубликованный товар. Сначала переместите в архив.',
  'Product not found': 'Товар не найден',
  'Product is already in the requested status':
    'Товар уже находится в запрашиваемом статусе',
  'Invalid status transition': 'Недопустимый переход статуса',
  'Invalid product ID': 'Некорректный ID товара',
};

const PRODUCT_OPTS = { translations: PRODUCT_ERROR_TRANSLATIONS };

const S3_ORIGIN = 'https://t3.storage.dev/loyality';
const PUBLIC_ORIGIN = 'https://loyality.t3.tigrisfiles.io';
const MEDIA_PROCESSING_TIMEOUT_MS = 120_000;

// ---------------------------------------------------------------------------
// Product CRUD + status FSM
// ---------------------------------------------------------------------------

export function fetchProducts({
  offset = 0,
  limit = 50,
  status,
  brandId,
  sortBy,
} = {}) {
  const params = new URLSearchParams();
  params.set('offset', String(offset));
  params.set('limit', String(limit));
  if (status) params.set('status', status);
  if (brandId) params.set('brand_id', brandId);
  if (sortBy) params.set('sort_by', sortBy);

  return apiClient.get(
    `/api/catalog/products?${params.toString()}`,
    PRODUCT_OPTS,
  );
}

export function fetchProductCounts() {
  return apiClient.get('/api/catalog/products/counts', PRODUCT_OPTS);
}

export function getProduct(productId) {
  return apiClient.get(`/api/catalog/products/${productId}`, PRODUCT_OPTS);
}

export function getProductCompleteness(productId) {
  return apiClient.get(
    `/api/catalog/products/${productId}/completeness`,
    PRODUCT_OPTS,
  );
}

export function createProduct(payload) {
  return apiClient.post('/api/catalog/products', payload, PRODUCT_OPTS);
}

export function updateProduct(productId, payload) {
  return apiClient.patch(
    `/api/catalog/products/${productId}`,
    payload,
    PRODUCT_OPTS,
  );
}

export function deleteProduct(productId) {
  return apiClient.del(`/api/catalog/products/${productId}`, PRODUCT_OPTS);
}

export function changeProductStatus(productId, status) {
  return apiClient.patch(
    `/api/catalog/products/${productId}/status`,
    { status },
    PRODUCT_OPTS,
  );
}

// ---------------------------------------------------------------------------
// Variants & SKUs
// ---------------------------------------------------------------------------

export function createVariant(productId, payload) {
  return apiClient.post(
    `/api/catalog/products/${productId}/variants`,
    payload,
    PRODUCT_OPTS,
  );
}

export function updateVariant(productId, variantId, payload) {
  return apiClient.patch(
    `/api/catalog/products/${productId}/variants/${variantId}`,
    payload,
    PRODUCT_OPTS,
  );
}

export function deleteVariant(productId, variantId) {
  return apiClient.del(
    `/api/catalog/products/${productId}/variants/${variantId}`,
    PRODUCT_OPTS,
  );
}

export function generateSkus(productId, variantId, payload) {
  return apiClient.post(
    `/api/catalog/products/${productId}/variants/${variantId}/skus/generate`,
    payload,
    PRODUCT_OPTS,
  );
}

export function listSkus(productId, variantId) {
  return apiClient.get(
    `/api/catalog/products/${productId}/variants/${variantId}/skus`,
    PRODUCT_OPTS,
  );
}

export function updateSku(productId, variantId, skuId, payload) {
  return apiClient.patch(
    `/api/catalog/products/${productId}/variants/${variantId}/skus/${skuId}`,
    payload,
    PRODUCT_OPTS,
  );
}

// ---------------------------------------------------------------------------
// Attributes
// ---------------------------------------------------------------------------

export function bulkAssignAttrs(productId, payload) {
  return apiClient.post(
    `/api/catalog/products/${productId}/attributes/bulk`,
    payload,
    PRODUCT_OPTS,
  );
}

export function deleteProductAttribute(productId, attributeId) {
  return apiClient.del(
    `/api/catalog/products/${productId}/attributes/${attributeId}`,
    PRODUCT_OPTS,
  );
}

// ---------------------------------------------------------------------------
// Media — reservation, association, listing, mutation
// ---------------------------------------------------------------------------

export function reserveMediaUpload(payload) {
  return apiClient.post('/api/media/upload', payload, PRODUCT_OPTS);
}

export function confirmMedia(storageObjectId) {
  return apiClient.post(
    `/api/media/${storageObjectId}/confirm`,
    undefined,
    PRODUCT_OPTS,
  );
}

export function deleteMedia(storageObjectId) {
  return apiClient.del(`/api/media/${storageObjectId}`, PRODUCT_OPTS);
}

export function listProductMedia(productId) {
  return apiClient.get(
    `/api/catalog/products/${productId}/media`,
    PRODUCT_OPTS,
  );
}

export function associateMedia(productId, payload) {
  return apiClient.post(
    `/api/catalog/products/${productId}/media`,
    payload,
    PRODUCT_OPTS,
  );
}

export function updateMediaAsset(productId, mediaId, payload) {
  return apiClient.patch(
    `/api/catalog/products/${productId}/media/${mediaId}`,
    payload,
    PRODUCT_OPTS,
  );
}

export function deleteMediaAsset(productId, mediaId) {
  return apiClient.del(
    `/api/catalog/products/${productId}/media/${mediaId}`,
    PRODUCT_OPTS,
  );
}

export function reorderMedia(productId, payload) {
  return apiClient.post(
    `/api/catalog/products/${productId}/media/reorder`,
    payload,
    PRODUCT_OPTS,
  );
}

// ---------------------------------------------------------------------------
// Media — direct S3 upload (BFF proxy because of CSP connect-src 'self')
// ---------------------------------------------------------------------------

export async function uploadToS3(presignedUrl, file) {
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
    throw new ApiError({
      message: data?.error?.message || 'File upload to S3 failed',
      code: 'S3_UPLOAD_FAILED',
      status: res.status,
    });
  }
}

export function extractRawUrl(presignedUrl) {
  const [urlWithoutQuery] = presignedUrl.split('?');
  return urlWithoutQuery.replace(S3_ORIGIN, PUBLIC_ORIGIN);
}

// ---------------------------------------------------------------------------
// Media — SSE status stream + binary helper
// ---------------------------------------------------------------------------

export function subscribeMediaStatus(
  storageObjectId,
  { timeout = MEDIA_PROCESSING_TIMEOUT_MS, signal } = {},
) {
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource(`/api/media/${storageObjectId}/status`);
    let settled = false;

    const timeoutId = setTimeout(() => {
      if (settled) return;
      settled = true;
      eventSource.close();
      reject(
        new ApiError({
          message: 'Media processing timed out',
          code: 'MEDIA_PROCESSING_TIMEOUT',
        }),
      );
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
        reject(
          new ApiError({
            message: data.error || 'Media processing failed',
            code: 'MEDIA_PROCESSING_FAILED',
          }),
        );
      }
    });

    eventSource.onerror = () => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(
        new ApiError({
          message: 'SSE connection lost',
          code: 'SSE_CONNECTION_ERROR',
        }),
      );
    };
  });
}

export async function fetchImageAsFile(imageUrl) {
  const res = await fetch(
    `/api/media/proxy?url=${encodeURIComponent(imageUrl)}`,
    {
      credentials: 'include',
    },
  );
  if (!res.ok) {
    throw new ApiError({
      message: 'Не удалось загрузить изображение',
      code: 'IMAGE_FETCH_FAILED',
      status: res.status,
    });
  }
  const blob = await res.blob();
  const ext = blob.type.split('/')[1] || 'jpg';
  return new File([blob], `image.${ext}`, { type: blob.type });
}
