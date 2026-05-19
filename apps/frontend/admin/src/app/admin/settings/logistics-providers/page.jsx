'use client';

import { useMemo, useState } from 'react';
import {
  PROVIDER_CODES,
  ProviderAccountCard,
  providerLabel,
  useProviderAccounts,
  useSetProviderAccountActive,
} from '@/entities/logistics-provider';
import {
  DeleteProviderConfirmModal,
  ProviderAccountFormModal,
  RegistryStatusPanel,
  useProviderRegistryRefresh,
} from '@/features/logistics-provider-form';
import { ApiErrorState } from '@/shared/ui/ApiErrorState';
import { Checkbox } from '@/shared/ui/Checkbox';
import { Skeleton } from '@/shared/ui/Skeleton';
import { useToast } from '@/shared/hooks/useToast';
import { cn } from '@/shared/lib/utils';

/**
 * Settings → «Провайдеры доставки». CRUD over logistics provider accounts
 * (CDEK / Yandex Delivery / DobroPost).
 *
 * Permission note (task §6.4): the backend gates these endpoints behind
 * `logistics:admin`, but `useAuth()` does not expose the permission list —
 * so the page can't be hidden pre-emptively. Instead a 403 from the list
 * query renders a dedicated "недостаточно прав" panel.
 *
 * Filtering / sorting is client-side: the list is small (a handful of
 * config rows), so instant chips beat a refetch round-trip.
 */
export default function LogisticsProvidersPage() {
  const { data, isPending, error, refetch } = useProviderAccounts();
  const setActiveMutation = useSetProviderAccountActive();
  const { refreshRegistry } = useProviderRegistryRefresh();
  const toast = useToast();

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const [providerFilter, setProviderFilter] = useState('all');
  const [onlyActive, setOnlyActive] = useState(false);

  const accounts = useMemo(() => data?.items ?? [], [data]);
  const activeCount = useMemo(
    () => accounts.filter((account) => account.isActive).length,
    [accounts],
  );

  const visible = useMemo(() => {
    return accounts
      .filter((account) => {
        if (
          providerFilter !== 'all' &&
          account.providerCode !== providerFilter
        ) {
          return false;
        }
        if (onlyActive && !account.isActive) return false;
        return true;
      })
      .sort(
        (a, b) =>
          Number(b.isActive) - Number(a.isActive) ||
          String(a.name).localeCompare(String(b.name), 'ru'),
      );
  }, [accounts, providerFilter, onlyActive]);

  function handleToggleActive(account) {
    setActiveMutation.mutate(
      { id: account.id, isActive: !account.isActive },
      {
        onSuccess: () =>
          refreshRegistry(
            account.isActive ? 'Провайдер отключён' : 'Провайдер активирован',
          ),
        onError: (err) =>
          toast.error(err?.message ?? 'Не удалось изменить статус'),
      },
    );
  }

  function resetFilters() {
    setProviderFilter('all');
    setOnlyActive(false);
  }

  const hasAccounts = accounts.length > 0;
  const filterChips = [
    { value: 'all', label: 'Все' },
    ...PROVIDER_CODES.map((code) => ({
      value: code,
      label: providerLabel(code),
    })),
  ];

  return (
    <section>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-app-text text-xl font-semibold">
            Провайдеры доставки
          </h2>
          {hasAccounts && (
            <p className="text-app-muted mt-0.5 text-sm">
              Всего {accounts.length} · активных {activeCount}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Добавить провайдера
        </button>
      </div>

      <RegistryStatusPanel />

      {hasAccounts && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {filterChips.map((chip) => {
            const selected = providerFilter === chip.value;
            return (
              <button
                key={chip.value}
                type="button"
                aria-pressed={selected}
                onClick={() => setProviderFilter(chip.value)}
                className={cn(
                  'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
                  selected
                    ? 'border-app-text-dark bg-app-text-dark text-white'
                    : 'border-app-border text-app-text-dark hover:bg-app-card',
                )}
              >
                {chip.label}
              </button>
            );
          })}
          <label className="text-app-text-dark ml-auto flex cursor-pointer items-center gap-2 text-sm">
            <Checkbox checked={onlyActive} onChange={setOnlyActive} />
            Только активные
          </label>
        </div>
      )}

      {error ? (
        error.status === 403 ? (
          <div
            role="alert"
            className="flex flex-col items-center gap-2 rounded-2xl bg-red-50 px-6 py-12 text-center"
          >
            <p className="text-sm font-semibold text-red-700">
              Недостаточно прав
            </p>
            <p className="max-w-md text-sm text-red-700">
              Для управления провайдерами доставки нужен доступ{' '}
              <code className="font-mono">logistics:admin</code> — он есть
              только у роли «admin».
            </p>
          </div>
        ) : (
          <ApiErrorState error={error} onRetry={() => refetch()} />
        )
      ) : isPending ? (
        <div
          role="status"
          aria-label="Загружаем провайдеров"
          className="space-y-3"
        >
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-36 w-full rounded-2xl" />
          ))}
        </div>
      ) : accounts.length === 0 ? (
        <div className="border-app-border flex flex-col items-center gap-3 rounded-2xl border border-dashed py-14 text-center">
          <p className="text-app-text-dark text-sm font-medium">
            Провайдеры доставки ещё не настроены
          </p>
          <p className="text-app-muted max-w-sm text-sm">
            Добавьте аккаунт CDEK, Yandex Delivery или DobroPost, чтобы
            рассчитывать стоимость и бронировать доставку.
          </p>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="text-app-text text-sm font-medium underline hover:no-underline"
          >
            Добавить первого
          </button>
        </div>
      ) : visible.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-app-muted text-sm">
            Под фильтр ничего не подошло.
          </p>
          <button
            type="button"
            onClick={resetFilters}
            className="text-app-text text-sm font-medium underline hover:no-underline"
          >
            Сбросить фильтры
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map((account) => (
            <ProviderAccountCard
              key={account.id}
              account={account}
              onEdit={setEditTarget}
              onDelete={setDeleteTarget}
              onToggleActive={handleToggleActive}
              toggling={
                setActiveMutation.isPending &&
                setActiveMutation.variables?.id === account.id
              }
            />
          ))}
        </div>
      )}

      <ProviderAccountFormModal
        open={createOpen}
        mode="create"
        onClose={() => setCreateOpen(false)}
      />
      <ProviderAccountFormModal
        open={Boolean(editTarget)}
        mode="edit"
        accountId={editTarget?.id}
        onClose={() => setEditTarget(null)}
      />
      <DeleteProviderConfirmModal
        open={Boolean(deleteTarget)}
        account={deleteTarget}
        onClose={() => setDeleteTarget(null)}
      />
    </section>
  );
}
