'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createSupplier } from './suppliers';
import { supplierKeys } from './keys';

export function useCreateSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createSupplier,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: supplierKeys.lists() });
    },
  });
}
