'use client';

import { useEffect } from 'react';
import {
  ProviderLogo,
  ProviderName,
  useDeleteProviderAccount,
} from '@/entities/logistics-provider';
import { Modal } from '@/shared/ui/Modal';
import { useProviderRegistryRefresh } from '../model/useProviderRegistryRefresh';

/**
 * Hard-delete confirmation. The backend removes the row outright (204), so
 * the copy is explicit about irreversibility. Error codes are already mapped
 * to Russian by the entity api layer — we show `error.message` as-is.
 */
export function DeleteProviderConfirmModal({ open, onClose, account }) {
  const mutation = useDeleteProviderAccount();
  const { refreshRegistry } = useProviderRegistryRefresh();

  useEffect(() => {
    if (open) mutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!account) return null;

  function handleConfirm() {
    mutation.mutate(account.id, {
      onSuccess: async () => {
        await refreshRegistry('Аккаунт удалён');
        onClose();
      },
    });
  }

  return (
    <Modal open={open} onClose={onClose} size="sm" title="Удалить провайдера">
      <div className="mt-4 space-y-4">
        <div className="border-app-border flex items-center gap-3 rounded-lg border px-3 py-2.5">
          <ProviderLogo
            code={account.providerCode}
            className="h-8 w-8 rounded-lg"
          />
          <span className="min-w-0">
            <span className="text-app-text-dark block truncate text-sm font-medium">
              {account.name}
            </span>
            <ProviderName
              code={account.providerCode}
              className="text-app-muted block text-xs"
              logoClassName="mt-0.5 h-4"
            />
          </span>
        </div>

        <p className="text-app-text-dark text-sm">
          Аккаунт будет удалён безвозвратно. Если он используется в расчётах
          доставки — сначала настройте замену.
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
