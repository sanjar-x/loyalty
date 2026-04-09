'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query-keys';
import type {
  PaginatedResponse,
  Product,
  Category,
  Brand,
} from '@/types';

// ── Filters ──────────────────────────────────────────────────────────

export interface ProductFilters {
  skip?: number;
  limit?: number;
  category_id?: string;
  type_id?: string;
  brand_id?: string;
  price_min?: number;
  price_max?: number;
}

export interface SearchBrandsParams {
  q?: string;
  limit?: number;
  offset?: number;
}

// ── Helpers ──────────────────────────────────────────────────────────

/** Build URLSearchParams from a record, skipping undefined/null values. */
function toSearchParams(
  params: Record<string, string | number | undefined | null>,
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value != null) {
      result[key] = String(value);
    }
  }
  return result;
}

// ── Category with types response ─────────────────────────────────────

export interface CategoryWithTypes {
  id: string;
  name: string;
  slug: string;
  types: Array<{ id: string; name: string; categoryId: string }>;
}

// ── Queries ──────────────────────────────────────────────────────────

const THIRTY_MINUTES = 30 * 60 * 1000;

export function useProducts(filters: ProductFilters = {}) {
  return useQuery({
    queryKey: queryKeys.products.list(filters as Record<string, unknown>),
    queryFn: () =>
      apiClient
        .get('api/v1/products/', {
          searchParams: toSearchParams({
            skip: filters.skip,
            limit: filters.limit,
            category_id: filters.category_id,
            type_id: filters.type_id,
            brand_id: filters.brand_id,
            price_min: filters.price_min,
            price_max: filters.price_max,
          }),
        })
        .json<PaginatedResponse<Product>>(),
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: queryKeys.products.detail(id),
    queryFn: () =>
      apiClient.get(`api/v1/products/${id}`).json<Product>(),
    enabled: !!id,
  });
}

export function useLatestProducts(limit: number = 10) {
  return useQuery({
    queryKey: queryKeys.products.latest(limit),
    queryFn: () =>
      apiClient
        .get('api/v1/products/latest', {
          searchParams: { limit: String(limit) },
        })
        .json<Product[]>(),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories.list(),
    queryFn: () =>
      apiClient.get('api/v1/categories').json<Category[]>(),
    staleTime: THIRTY_MINUTES,
  });
}

export function useCategoriesWithTypes() {
  return useQuery({
    queryKey: queryKeys.categories.withTypes(),
    queryFn: () =>
      apiClient.get('api/v1/types').json<CategoryWithTypes[]>(),
    staleTime: THIRTY_MINUTES,
  });
}

export function useBrands() {
  return useQuery({
    queryKey: queryKeys.brands.list(),
    queryFn: () => apiClient.get('api/v1/brands').json<Brand[]>(),
    staleTime: THIRTY_MINUTES,
  });
}

export function useSearchBrands(params: SearchBrandsParams = {}) {
  const searchKey = params.q ?? '';
  return useQuery({
    queryKey: queryKeys.brands.search(searchKey),
    queryFn: () =>
      apiClient
        .get('api/v1/brands/search', {
          searchParams: toSearchParams({
            q: params.q,
            limit: params.limit,
            offset: params.offset,
          }),
        })
        .json<Brand[]>(),
    enabled: !!params.q,
  });
}
