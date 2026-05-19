'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import {
  canPerformAction,
  OrderDetailsView,
  useOrder,
  useOrderHistory,
  useOrderTracking,
} from '@/entities/order';
import {
  ChangePickupPointModal,
  ForceCancelModal,
  HoldResumeModal,
  ProcureModal,
} from '@/features/order-actions';
import { cn } from '@/shared/lib/utils';

const ACTIONS = [
  { key: 'procure', label: 'Передать в закупку', tone: 'primary' },
  { key: 'hold', label: 'Поставить на hold', tone: 'warning' },
  { key: 'resume', label: 'Возобновить', tone: 'success' },
  { key: 'changePickup', label: 'Изменить пункт выдачи', tone: 'neutral' },
  { key: 'forceCancel', label: 'Принудительная отмена', tone: 'danger' },
];

const TONE_CLASS = {
  primary: 'bg-app-text-dark text-white hover:opacity-90',
  warning: 'bg-orange-600 text-white hover:opacity-90',
  success: 'bg-app-success text-white hover:opacity-90',
  danger: 'bg-app-danger text-white hover:opacity-90',
  neutral: 'bg-app-card text-app-text-dark hover:bg-app-divider-strong',
};

function ActionToolbar({ status, onOpen }) {
  return (
    <div className="flex flex-wrap gap-2">
      {ACTIONS.map(({ key, label, tone }) => {
        if (!canPerformAction(key, status)) return null;
        return (
          <button
            key={key}
            type="button"
            onClick={() => onOpen(key)}
            className={cn(
              'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              TONE_CLASS[tone],
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const [openAction, setOpenAction] = useState(null);

  const {
    data: order,
    isPending: orderLoading,
    error: orderError,
    refetch: refetchOrder,
  } = useOrder(orderId);

  // Tab content for the timeline / history surfaces — fetch them eagerly so
  // switching tabs feels instant. Both queries are guarded on `orderId` so
  // they don't fire before the route param resolves.
  const { data: tracking, isPending: trackingLoading } =
    useOrderTracking(orderId);
  const { data: history, isPending: historyLoading } = useOrderHistory(orderId);

  if (orderLoading && !order) {
    return (
      <div className="text-app-muted px-6 py-10 text-sm">Загрузка заказа…</div>
    );
  }

  if (orderError && !order) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl bg-red-50 px-6 py-12 text-center">
        <p className="text-sm text-red-700">
          {orderError?.message ?? 'Не удалось загрузить заказ'}
        </p>
        <button
          type="button"
          onClick={() => refetchOrder()}
          className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-medium text-white"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  if (!order) return null;

  const close = () => setOpenAction(null);

  return (
    <>
      <OrderDetailsView
        order={order}
        tracking={tracking}
        trackingLoading={trackingLoading}
        history={history ?? []}
        historyLoading={historyLoading}
        actionToolbar={
          <ActionToolbar status={order.status} onOpen={setOpenAction} />
        }
      />

      <ProcureModal
        open={openAction === 'procure'}
        order={order}
        onClose={close}
      />
      <HoldResumeModal
        open={openAction === 'hold' || openAction === 'resume'}
        order={order}
        mode={openAction === 'resume' ? 'resume' : 'hold'}
        onClose={close}
      />
      <ForceCancelModal
        open={openAction === 'forceCancel'}
        order={order}
        onClose={close}
      />
      <ChangePickupPointModal
        open={openAction === 'changePickup'}
        order={order}
        onClose={close}
      />
    </>
  );
}
