'use client';

import Link from 'next/link';

import { OrdersList } from '@/entities/order';
import { StatusTabs, useOrderFilters } from '@/features/order-filter';

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl bg-red-50 px-6 py-12 text-center">
      <p className="text-sm text-red-700">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-medium text-white"
      >
        Повторить
      </button>
    </div>
  );
}

function LoadMore({ onClick, loading, hasMore }) {
  if (!hasMore) return null;
  return (
    <div className="flex justify-center pt-2">
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className="border-app-border text-app-text-dark hover:bg-app-card rounded-xl border px-5 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? 'Загружаем…' : 'Показать ещё'}
      </button>
    </div>
  );
}

export default function OrdersPage() {
  const {
    groupKey,
    setGroupKey,
    search,
    setSearch,
    items,
    loading,
    error,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useOrderFilters();

  return (
    <section className="animate-fadeIn">
      {/*
        Walk-in CTA is visible to everyone for the MVP — permission
        gating (orders:create_offline) requires /api/auth/me to expose
        scopes, which isn't wired yet. Backend still rejects with 403
        INSUFFICIENT_PERMISSIONS, surfaced via toast in
        useSubmitWalkInOrder. Tracked as a separate ticket.
      */}
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-app-text-dark text-[40px] leading-[44px] font-bold tracking-[-1px]">
          Заказы
        </h1>
        <Link
          href="/admin/orders/new"
          className="bg-app-text-dark hover:bg-app-text rounded-2xl px-5 py-2.5 text-sm font-medium text-white transition-colors"
        >
          + Walk-in заказ
        </Link>
      </div>

      <div className="mb-5">
        <StatusTabs activeKey={groupKey} onChange={setGroupKey} />
      </div>

      <div className="mb-4">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Поиск по номеру заказа или identityId"
          className="border-app-border focus:border-app-text-dark w-full max-w-md rounded-lg border px-3 py-2 text-sm transition-colors outline-none"
        />
      </div>

      {error ? (
        <ErrorBanner
          message={error?.message ?? 'Не удалось загрузить заказы'}
          onRetry={() => refetch()}
        />
      ) : (
        <>
          <OrdersList orders={items} loading={loading} />
          <LoadMore
            onClick={() => fetchNextPage()}
            loading={isFetchingNextPage}
            hasMore={Boolean(hasNextPage)}
          />
        </>
      )}
    </section>
  );
}
