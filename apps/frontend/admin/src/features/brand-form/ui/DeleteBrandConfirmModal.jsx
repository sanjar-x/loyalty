'use client';

import { useEffect } from 'react';
import { useDeleteBrand } from '@/entities/brand';
import { Modal } from '@/shared/ui/Modal';

/**
 * Confirmation modal with conflict-aware error rendering. Backend
 * returns BRAND_HAS_PRODUCTS (translated by entities/brand) when the
 * brand has attached products — that lands as a Russian message in
 * the alert below; the apiClient already mapped the code, so we just
 * show `mutation.error.message` verbatim.
 */
export function DeleteBrandConfirmModal({ open, onClose, brand }) {
  const mutation = useDeleteBrand();

  useEffect(() => {
    if (open) mutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!brand) return null;

  function handleConfirm() {
    mutation.mutate(brand.id, { onSuccess: onClose });
  }

  return (
    <Modal open={open} onClose={onClose} size="sm" title="Удалить бренд">
      <div className="mt-4 space-y-4">
        <p className="text-app-text-dark text-sm">
          Подтвердите удаление бренда{' '}
          <strong className="font-semibold">{brand.name}</strong>.
        </p>
        {mutation.error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {mutation.error.message}
          </div>
        )}
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={mutation.isPending}
            className="text-app-muted hover:text-app-text-dark px-3 py-2 text-sm font-medium"
          >
            Отмена
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={mutation.isPending}
            className="bg-app-danger rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? 'Удаляем…' : 'Удалить'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
