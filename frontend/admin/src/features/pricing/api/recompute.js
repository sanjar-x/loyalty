import { apiClient } from '@/shared/api/client-fetch';

export const recomputeSku = (skuId) =>
  apiClient.post(`/api/pricing/recompute/skus/${skuId}`);

export const recomputeContext = (contextId) =>
  apiClient.post(`/api/pricing/recompute/contexts/${contextId}`);

export const recomputeCategory = (categoryId) =>
  apiClient.post(`/api/pricing/recompute/categories/${categoryId}`);

export const recomputeSupplier = (supplierId) =>
  apiClient.post(`/api/pricing/recompute/suppliers/${supplierId}`);
