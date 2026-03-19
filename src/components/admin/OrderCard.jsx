'use client';

import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { CopyMark } from '@/components/ui/CopyMark';
import { STATUS_PILL_LABELS } from '@/lib/constants';
import { cn, formatCurrency, formatDateTime } from '@/lib/utils';

const statusClassName = {
  placed: 'bg-white text-[#2a2d33]',
  in_transit: 'bg-[#2f3238] text-white',
  pickup_point: 'bg-[#eceff4] text-[#323742]',
  canceled: 'bg-[#f4f4f5] text-[#81858d]',
  received: 'bg-white text-[#2a2d33]',
};

function StatusButton({ label, withEdit = false, className, onClick }) {
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        onClick?.();
      }}
      className={cn(
        'inline-flex h-[38px] items-center gap-2 rounded-[12px] bg-white px-4 text-base leading-5 font-medium text-[#2d2d2d]',
        className,
      )}
    >
      <span className="h-4 w-4 rounded-full border border-[#8f8f8f]" />
      <span>{label}</span>
      {withEdit && (
        <span className="text-sm text-[#8f8f8f]">
          <svg
            width="18"
            height="18"
            viewBox="0 0 18 18"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M9.01763 4.48623L0.805054 12.6987V16.8049L4.91134 16.8049L13.1239 8.59245M9.01763 4.48623L11.9625 1.54139L11.9643 1.53964C12.3696 1.13427 12.5727 0.931225 12.8067 0.855175C13.0129 0.788184 13.235 0.788184 13.4412 0.855175C13.6751 0.931171 13.8779 1.13398 14.2827 1.53878L16.0688 3.32478C16.4753 3.73132 16.6787 3.93468 16.7548 4.16907C16.8218 4.37525 16.8218 4.59734 16.7548 4.80352C16.6787 5.03774 16.4756 5.2408 16.0697 5.64675L16.0688 5.64762L13.1239 8.59245M9.01763 4.48623L13.1239 8.59245"
              stroke="#7E7E7E"
              strokeWidth="1.61"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      )}
    </button>
  );
}

export function OrderCard({ order, onOpenStatusModal }) {
  const router = useRouter();
  const isPlaced = order.status === 'placed';
  const showItemActions = isPlaced && order.items.length > 1;
  const summaryLabel = showItemActions
    ? `Оформлен ${order.items.length} из ${order.items.length}`
    : STATUS_PILL_LABELS[order.status];
  const openOrderPage = () => router.push(`/admin/orders/${order.id}`);
  const openStatusModal = () => {
    if (onOpenStatusModal) {
      onOpenStatusModal(order);
      return;
    }
    openOrderPage();
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={openOrderPage}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openOrderPage();
        }
      }}
      className="cursor-pointer overflow-hidden rounded-2xl bg-[#f4f3f1]"
    >
      <div className="flex flex-col items-start justify-between gap-3 px-5 pt-4 pb-2 md:flex-row md:items-center">
        <div className="flex flex-wrap items-center gap-2 text-base leading-5 font-medium text-[#7e7e7e]">
          <span className="inline-flex items-center">
            №{order.orderNumber}
            <CopyMark text={order.orderNumber} />
          </span>
          <span>•</span>
          <span className="inline-flex items-center">
            {order.trackId}
            <CopyMark text={order.trackId} />
          </span>
          <span>•</span>
          <span>{formatDateTime(order.createdAt)}</span>
          {order.fromChina && (
            <span className="ml-1 rounded-full bg-[#f2e5c2] px-3 py-1 text-sm leading-5 font-medium text-[#5c4a17]">
              Из Китая
            </span>
          )}
        </div>

        {isPlaced ? (
          <StatusButton
            label={summaryLabel}
            withEdit
            className="shrink-0"
            onClick={openStatusModal}
          />
        ) : (
          <span
            className={cn(
              'rounded-full px-4 py-2 text-base leading-5 font-medium',
              statusClassName[order.status],
            )}
          >
            {STATUS_PILL_LABELS[order.status]}
          </span>
        )}
      </div>

      <div className="px-5 pt-1 pb-4">
        <div className="space-y-4">
          {order.items.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="flex min-w-0 items-start gap-3 text-left">
                <div className="rounded-lg bg-[#f4f3f1]">
                  <Image
                    src={item.image}
                    alt={item.title}
                    width={64}
                    height={64}
                    className="rounded"
                  />
                </div>

                <div className="min-w-0">
                  <div className="grid grid-cols-1 gap-y-1 sm:grid-cols-[246px_60px] sm:items-start sm:gap-x-[85px]">
                    <p className="h-[40px] w-full overflow-hidden text-[16px] leading-5 font-medium text-[#000000] sm:w-[246px]">
                      {item.title}
                    </p>
                    <p className="h-[19px] w-[60px] text-[16px] leading-5 font-medium whitespace-nowrap text-[#2d2d2d] sm:mt-[22px]">
                      {formatCurrency(item.price)}
                    </p>
                  </div>
                  <p className="mt-1 text-base leading-5 font-medium text-[#7e7e7e]">
                    Размер: {item.size}
                  </p>
                </div>
              </div>

              {showItemActions && (
                <div className="self-start sm:self-center">
                  <StatusButton label="Оформлен" onClick={openStatusModal} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="h-px bg-[#e0dedb]" />

      <div className="flex items-center justify-between px-5 py-3.5">
        <p className="text-xl leading-[120%] font-bold text-[#2d2d2d] capitalize">
          Итого
        </p>
        <p className="text-xl leading-[120%] font-bold text-[#2d2d2d] capitalize">
          {formatCurrency(order.total)}
        </p>
      </div>
    </div>
  );
}
