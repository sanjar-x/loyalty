'use client';

import { useRouter } from 'next/navigation';
import { CopyMark } from '@/shared/ui/CopyMark';
import { cn, formatCurrency, formatDateTime } from '@/shared/lib/utils';
import {
  CUSTOMER_FACING_STATUS_LABELS,
  ORDER_STATUS_LABELS,
} from '../lib/constants';

// `AdminOrderSchema` ships money in smallest currency units; the admin
// surface renders human-friendly amounts so we divide by 100 here.
function toUserAmount(amount) {
  if (typeof amount !== 'number') return 0;
  return amount / 100;
}

// Aggregate every distinct supplier_type that appears across the order's
// items. Backend doesn't denormalise the breakdown on the order itself, so
// we derive it here so the card can show «china × 2 + locked × 1» style
// breakdowns at a glance.
function summariseSuppliers(items = []) {
  const counts = new Map();
  for (const item of items) {
    if (!item?.supplierType) continue;
    counts.set(
      item.supplierType,
      (counts.get(item.supplierType) ?? 0) + (item.quantity ?? 1),
    );
  }
  return Array.from(counts.entries()).map(([type, qty]) => ({ type, qty }));
}

const SUPPLIER_LABELS = {
  cross_border_china: 'Из Китая',
  cross_border: 'Cross-border',
  warehouse: 'Со склада',
  preorder: 'Предзаказ',
};

const RAW_STATUS_TONE = {
  pending: 'bg-app-card text-app-text-dark',
  paid: 'bg-emerald-50 text-emerald-700',
  procured: 'bg-amber-50 text-amber-700',
  on_hold: 'bg-orange-50 text-orange-700',
  arrived_in_ru: 'bg-blue-50 text-blue-700',
  in_last_mile: 'bg-blue-50 text-blue-700',
  ready_for_pickup: 'bg-emerald-50 text-emerald-700',
  delivered: 'bg-app-success/10 text-app-success',
  returning: 'bg-orange-50 text-orange-700',
  returned: 'bg-app-card text-app-muted',
  cancelled: 'bg-app-card text-app-muted',
  refunding: 'bg-orange-50 text-orange-700',
  refunded: 'bg-app-card text-app-muted',
  expired: 'bg-app-card text-app-muted',
};

export function OrderCard({ order }) {
  const router = useRouter();
  const open = () => router.push(`/admin/orders/${order.orderId}`);
  const supplierBreakdown = summariseSuppliers(order.items);
  const totalAmount = toUserAmount(order.totalAmount);

  const customerFacingLabel =
    CUSTOMER_FACING_STATUS_LABELS[order.customerFacingStatus] ??
    order.customerFacingStatus;
  const rawStatusLabel = ORDER_STATUS_LABELS[order.status] ?? order.status;
  const rawStatusTone =
    RAW_STATUS_TONE[order.status] ?? 'bg-app-card text-app-muted';

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Заказ ${order.orderNumber}`}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          open();
        }
      }}
      className={cn(
        'bg-app-card cursor-pointer overflow-hidden rounded-2xl',
        'focus-visible:ring-app-text focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
      )}
    >
      <div className="flex flex-col gap-3 px-5 pt-4 pb-3 md:flex-row md:items-center md:justify-between">
        <div className="text-app-muted flex flex-wrap items-center gap-2 text-base font-medium">
          <span className="inline-flex items-center font-mono text-[15px]">
            {order.orderNumber}
            <CopyMark text={order.orderNumber} />
          </span>
          <span>•</span>
          <span>{formatDateTime(order.createdAt)}</span>
          {supplierBreakdown.length > 0 && <span>•</span>}
          {supplierBreakdown.map(({ type, qty }) => (
            <span
              key={type}
              className="bg-app-badge-china text-app-badge-china-text rounded-full px-3 py-1 text-sm leading-5"
            >
              {SUPPLIER_LABELS[type] ?? type} × {qty}
            </span>
          ))}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span
            className={cn(
              'rounded-full px-3 py-1 text-sm leading-5 font-medium',
              rawStatusTone,
            )}
            title={`raw: ${order.status}`}
          >
            {rawStatusLabel}
          </span>
          <span className="bg-app-text-dark rounded-full px-3 py-1 text-sm leading-5 font-medium text-white">
            {customerFacingLabel}
          </span>
        </div>
      </div>

      <div className="px-5 pb-3">
        <ul className="space-y-1 text-sm">
          {order.items.map((item) => (
            <li
              key={item.itemId}
              className="text-app-text-dark flex items-baseline justify-between gap-3"
            >
              <span className="min-w-0 truncate">
                {item.productName}
                {item.variantLabel ? (
                  <span className="text-app-muted ml-1">
                    · {item.variantLabel}
                  </span>
                ) : null}
                <span className="text-app-muted ml-1">× {item.quantity}</span>
              </span>
              <span className="text-app-muted shrink-0">
                {formatCurrency(toUserAmount(item.lineTotalAmount))}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-app-divider h-px" />

      <div className="flex items-center justify-between px-5 py-3.5">
        <p className="text-app-text-dark text-base font-semibold">
          Итого ·{' '}
          <span className="text-app-muted font-medium">{order.currency}</span>
        </p>
        <p className="text-app-text-dark text-xl leading-[120%] font-bold">
          {formatCurrency(totalAmount)}
        </p>
      </div>
    </div>
  );
}
