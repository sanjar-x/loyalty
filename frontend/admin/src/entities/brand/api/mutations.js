'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createBrand } from './brands';
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
