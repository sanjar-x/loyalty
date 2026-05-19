'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  bulkCreateBrands,
  createBrand,
  deleteBrand,
  updateBrand,
} from './brands';
import { brandKeys } from './keys';

export function useCreateBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBrand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: brandKeys.all });
    },
  });
}

export function useUpdateBrand(brandId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => updateBrand(brandId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: brandKeys.detail(brandId) });
      queryClient.invalidateQueries({ queryKey: brandKeys.lists() });
    },
  });
}

export function useDeleteBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (brandId) => deleteBrand(brandId),
    onSuccess: (_, brandId) => {
      queryClient.removeQueries({ queryKey: brandKeys.detail(brandId) });
      queryClient.invalidateQueries({ queryKey: brandKeys.lists() });
    },
  });
}

export function useBulkCreateBrands() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items) => bulkCreateBrands(items),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: brandKeys.lists() });
    },
  });
}
