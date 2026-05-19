'use client';

import { useCallback, useRef, useState } from 'react';

import { useReorderBindings } from '@/entities/attribute-template';

/**
 * DnD reorder hook for `<BindingsList>` — same shape as
 * `useImageReorder` (entities/product) but talks to the
 * `attribute-templates/.../attributes/reorder` BFF route.
 *
 * Usage:
 *
 *   const { reorder, isPending, error, clearError } = useBindingsReorder({
 *     templateId,
 *     onLocalReorder: (next) => setLocal(next),
 *   });
 *   reorder(prev, next);   // arrays of bindings (with id + sortOrder)
 *
 * `onLocalReorder` is called synchronously so the UI never flickers,
 * the backend POST follows. On failure we roll back via the same
 * callback and surface the error so the consumer can toast.
 */
export function useBindingsReorder({ templateId, onLocalReorder } = {}) {
  const [error, setError] = useState(null);
  const previousOrderRef = useRef(null);

  const mutation = useReorderBindings(templateId);
  const { mutate: persist } = mutation;

  const reorder = useCallback(
    (prev, next) => {
      previousOrderRef.current = prev;
      onLocalReorder?.(next);
      setError(null);

      if (!templateId) return;

      const items = next
        .map((binding, idx) =>
          binding.id ? { bindingId: binding.id, sortOrder: idx } : null,
        )
        .filter(Boolean);
      if (items.length === 0) return;

      persist(items, {
        onError: (err) => {
          setError(err);
          if (previousOrderRef.current) {
            onLocalReorder?.(previousOrderRef.current);
          }
        },
      });
    },
    [templateId, onLocalReorder, persist],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    reorder,
    isPending: mutation.isPending,
    error,
    clearError,
  };
}
