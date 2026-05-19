'use client';

import { useState } from 'react';
import Link from 'next/link';
import { CopyMark } from '@/shared/ui/CopyMark';
import { cn, formatCurrency, formatDateTime } from '@/shared/lib/utils';
import {
  CUSTOMER_FACING_STATUS_LABELS,
  ORDER_STATUS_LABELS,
} from '../lib/constants';
import { OrderTrackingTimeline } from './OrderTrackingTimeline';
import { OrderStateHistoryTable } from './OrderStateHistoryTable';
import { RecipientSnapshotPanel } from './RecipientSnapshotPanel';

const TABS = [
  { key: 'details', label: 'Детали' },
  { key: 'tracking', label: 'Трекинг' },
  { key: 'history', label: 'История' },
];

function toUserAmount(amount) {
  if (typeof amount !== 'number') return 0;
  return amount / 100;
}

const SUPPLIER_LABELS = {
  cross_border_china: 'Из Китая',
  cross_border: 'Cross-border',
  warehouse: 'Со склада',
  preorder: 'Предзаказ',
};

/**
 * Detail surface for a single order.
 *
 * Pure presentational — actual API loading + mutation logic lives in
 * `app/admin/orders/[orderId]/page.jsx` so we can chain `useOrder` /
 * `useOrderTracking` / `useOrderHistory` and the order-actions mutations.
 *
 * The `actionToolbar` prop is a render-slot for the conditional action
 * toolbar (Procure / Hold / Resume / Force-cancel / Change pickup); the
 * page composes those buttons against the FSM gates exposed by
 * `canPerformAction()` and feeds them in here.
 */
export function OrderDetailsView({
  order,
  tracking,
  trackingLoading,
  history,
  historyLoading,
  actionToolbar = null,
}) {
  const [tab, setTab] = useState('details');

  const customerFacingLabel =
    CUSTOMER_FACING_STATUS_LABELS[order.customerFacingStatus] ??
    order.customerFacingStatus;
  const rawStatusLabel = ORDER_STATUS_LABELS[order.status] ?? order.status;

  return (
    <section className="animate-fadeIn">
      {/* Header — order number, statuses, action toolbar */}
      <div className="mb-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Link
            href="/admin/orders"
            className="bg-app-card text-app-text-dark inline-flex h-10 items-center gap-2 rounded-2xl px-3 text-sm font-medium"
          >
            ← Заказы
          </Link>
          <span className="bg-app-card inline-flex h-10 items-center rounded-2xl px-3 font-mono text-sm font-medium">
            {order.orderNumber}
            <CopyMark text={order.orderNumber} />
          </span>
          <span className="text-app-muted text-sm">
            {formatDateTime(order.createdAt)}
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="bg-app-text-dark rounded-full px-3 py-1 text-sm font-medium text-white"
              title={`raw: ${order.status}`}
            >
              {rawStatusLabel}
            </span>
            <span className="bg-app-card text-app-text-dark rounded-full px-3 py-1 text-sm font-medium">
              Клиент: {customerFacingLabel}
            </span>
            {order.holdReason ? (
              <span className="rounded-full bg-orange-50 px-3 py-1 text-sm font-medium text-orange-700">
                Hold: {order.holdReason}
                {order.holdUntil
                  ? ` · до ${formatDateTime(order.holdUntil)}`
                  : ''}
              </span>
            ) : null}
            {order.cancellationReason ? (
              <span className="rounded-full bg-red-50 px-3 py-1 text-sm font-medium text-red-700">
                Отмена: {order.cancellationReason}
              </span>
            ) : null}
          </div>
          {actionToolbar}
        </div>
      </div>

      {/* Tabs */}
      <div
        role="tablist"
        className="border-app-border mb-5 flex gap-1 border-b"
      >
        {TABS.map((t) => {
          const selected = tab === t.key;
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={selected}
              type="button"
              onClick={() => setTab(t.key)}
              className={cn(
                '-mb-px rounded-t-lg px-4 py-2 text-sm font-medium transition-colors',
                selected
                  ? 'border-app-text-dark text-app-text-dark border-b-2'
                  : 'text-app-muted hover:text-app-text-dark',
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'details' && <DetailsTab order={order} />}
      {tab === 'tracking' && (
        <OrderTrackingTimeline tracking={tracking} loading={trackingLoading} />
      )}
      {tab === 'history' && (
        <OrderStateHistoryTable entries={history} loading={historyLoading} />
      )}
    </section>
  );
}

function DetailsTab({ order }) {
  const totalAmount = toUserAmount(order.totalAmount);
  const lineSubtotal = (order.items ?? []).reduce(
    (sum, item) => sum + (item.lineTotalAmount ?? 0),
    0,
  );

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-4">
        <article className="bg-app-card rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-app-text-dark text-lg font-semibold">
              Состав заказа
            </h2>
            <span className="text-app-muted text-sm">
              {order.items.length} позиций
            </span>
          </div>

          <ul className="divide-app-border divide-y">
            {order.items.map((item) => (
              <li
                key={item.itemId}
                className="grid gap-1 py-3 first:pt-0 last:pb-0"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-app-text-dark min-w-0 truncate text-base font-medium">
                    {item.productName}
                  </p>
                  <p className="text-app-text-dark shrink-0 text-base font-semibold">
                    {formatCurrency(toUserAmount(item.lineTotalAmount))}
                  </p>
                </div>
                <div className="text-app-muted flex flex-wrap items-center gap-2 text-xs">
                  {item.variantLabel && <span>{item.variantLabel}</span>}
                  <span>× {item.quantity}</span>
                  <span>·</span>
                  <span>
                    {formatCurrency(toUserAmount(item.unitPriceAmount))}
                  </span>
                  <span>·</span>
                  <span className="bg-app-panel rounded px-1.5 py-0.5">
                    {SUPPLIER_LABELS[item.supplierType] ?? item.supplierType}
                  </span>
                  {item.crossBorderShipmentId && (
                    <span className="text-app-muted/80 ml-auto">
                      cb: {item.crossBorderShipmentId.slice(0, 8)}…
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </article>

        <RecipientSnapshotPanel snapshot={order.recipientSnapshot} />
      </div>

      <aside className="space-y-4">
        <article className="bg-app-card rounded-2xl p-5">
          <h3 className="text-app-text-dark mb-3 text-sm font-semibold">
            Пункт выдачи
          </h3>
          <p className="text-app-text-dark text-sm">
            {order.pickupCarrier} · {order.pickupPointId}
          </p>
        </article>

        <article className="bg-app-card rounded-2xl p-5">
          <h3 className="text-app-text-dark mb-3 text-sm font-semibold">
            Идентификаторы
          </h3>
          <dl className="text-app-muted space-y-1 text-xs">
            <Row term="orderId" value={order.orderId} />
            <Row term="identityId" value={order.identityId} />
            <Row term="cartId" value={order.cartId} />
            {order.paymentIntentId && (
              <Row term="paymentIntentId" value={order.paymentIntentId} />
            )}
            {order.crossBorderShipmentId && (
              <Row
                term="crossBorderShipmentId"
                value={order.crossBorderShipmentId}
              />
            )}
            {order.lastMileShipmentId && (
              <Row term="lastMileShipmentId" value={order.lastMileShipmentId} />
            )}
            {order.incomingDeclaration && (
              <Row
                term="incomingDeclaration"
                value={order.incomingDeclaration}
              />
            )}
          </dl>
        </article>

        <article className="bg-app-card rounded-2xl p-5">
          <h3 className="text-app-text-dark mb-3 text-sm font-semibold">
            Сумма
          </h3>
          <dl className="text-app-text-dark space-y-1 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-app-muted">Сумма позиций</dt>
              <dd>{formatCurrency(toUserAmount(lineSubtotal))}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-app-muted">Валюта</dt>
              <dd>{order.currency}</dd>
            </div>
            {order.cnyRateAtCheckout && (
              <div className="flex items-center justify-between">
                <dt className="text-app-muted">CNY rate</dt>
                <dd>{order.cnyRateAtCheckout}</dd>
              </div>
            )}
            <div className="border-app-border mt-2 flex items-center justify-between border-t pt-2 text-base font-semibold">
              <dt>Итого</dt>
              <dd>{formatCurrency(totalAmount)}</dd>
            </div>
          </dl>
        </article>
      </aside>
    </div>
  );
}

function Row({ term, value }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="font-medium">{term}</dt>
      <dd className="text-app-text-dark inline-flex items-center font-mono">
        <span className="truncate" title={value}>
          {String(value).slice(0, 10)}…
        </span>
        <CopyMark text={String(value)} />
      </dd>
    </div>
  );
}
