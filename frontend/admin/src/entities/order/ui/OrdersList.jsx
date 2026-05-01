import { OrderCard } from './OrderCard';

function OrderCardSkeleton() {
  return (
    <div className="bg-app-card animate-pulse rounded-2xl p-6">
      <div className="h-4 w-2/3 rounded bg-gray-200" />
      <div className="mt-4 h-20 rounded bg-gray-200" />
      <div className="mt-4 h-5 w-40 rounded bg-gray-200" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-app-card rounded-[10px] px-6 py-12 text-center">
      <p className="text-app-text text-xl font-semibold">Заказы не найдены</p>
      <p className="text-app-muted mt-1 text-sm">
        Попробуйте изменить фильтры, период или строку поиска.
      </p>
    </div>
  );
}

export function OrdersList({ orders, loading, onOpenStatusModal }) {
  if (loading) {
    return (
      <div className="space-y-4">
        <OrderCardSkeleton />
        <OrderCardSkeleton />
        <OrderCardSkeleton />
      </div>
    );
  }

  if (!orders?.length) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-4">
      {orders.map((order) => (
        <OrderCard
          key={order.id}
          order={order}
          onOpenStatusModal={onOpenStatusModal}
        />
      ))}
    </div>
  );
}
