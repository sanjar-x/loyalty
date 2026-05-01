'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import { Modal } from '@/shared/ui/Modal';
import { CopyMark } from '@/shared/ui/CopyMark';
import { cn, formatCurrency, formatDateTime } from '@/shared/lib/utils';

const STATUS_OPTIONS = ['Оформлен', 'В пути', 'Отменен'];
const DEFAULT_ITEM_STATUS = 'Оформлен';

function StatusMenuButton({ label, selected, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-base leading-5 font-medium text-black hover:bg-[#f4f4f4]"
    >
      <span className="inline-flex items-center gap-2">
        {label !== 'Отменен' ? (
          <span className="h-4 w-4 rounded-full border border-[#7f7f7f]" />
        ) : (
          <span className="w-4" />
        )}
        {label}
      </span>
      <span
        className={cn(
          'inline-flex h-5 w-5 items-center justify-center rounded-full text-xs leading-none',
          selected
            ? 'bg-app-text-dark text-white'
            : 'bg-[#ececec] text-transparent',
        )}
      >
        ✓
      </span>
    </button>
  );
}

export function OrderStatusModal({
  open,
  order,
  onClose,
  onSave,
  initialItemStatuses,
  initialTrackNumbers,
}) {
  const [trackNumbers, setTrackNumbers] = useState({});
  const [itemStatuses, setItemStatuses] = useState({});
  const [menuItemId, setMenuItemId] = useState(null);

  useEffect(() => {
    if (!open || !order) return;

    const initial = {};
    const initialTracks = {};
    order.items.forEach((item) => {
      initial[item.id] = initialItemStatuses?.[item.id] ?? DEFAULT_ITEM_STATUS;
      initialTracks[item.id] = initialTrackNumbers?.[item.id] ?? '';
    });
    setItemStatuses(initial);
    setTrackNumbers(initialTracks);
    setMenuItemId(null);
  }, [open, order, initialItemStatuses, initialTrackNumbers]);

  if (!order) return null;

  const completedCount = Object.values(itemStatuses).filter(
    (status) => status === DEFAULT_ITEM_STATUS,
  ).length;
  const summaryLabel =
    order.items.length > 1
      ? `Оформлен ${completedCount} из ${order.items.length}`
      : DEFAULT_ITEM_STATUS;

  const handleSave = () => {
    onSave({ orderId: order.id, itemStatuses, trackNumbers });
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="2xl"
      hidePadding
      className="bg-app-card max-h-[calc(100vh-24px)] overflow-y-auto"
    >
      <div className="px-6 pt-5 pb-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[26px] leading-8 font-bold tracking-[-0.42px] text-[#3a3a3a]">
            Изменить статус
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="relative h-6 w-6"
            aria-label="Закрыть"
          >
            <span className="absolute top-1/2 left-1/2 h-[3px] w-4 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-black" />
            <span className="absolute top-1/2 left-1/2 h-[3px] w-4 -translate-x-1/2 -translate-y-1/2 -rotate-45 bg-black" />
          </button>
        </div>

        <div className="rounded-2xl bg-[#efeeec] px-5 py-4">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div className="text-app-muted flex flex-wrap items-center gap-2 text-base leading-5 font-medium">
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
                <span className="bg-app-badge-china text-app-badge-china-text ml-1 rounded-full px-3 py-1 text-sm leading-5 font-medium">
                  Из Китая
                </span>
              )}
              <span className="rounded-full bg-[#2f2f2f] px-3 py-1 text-sm leading-5 font-medium text-white">
                Оригинал
              </span>
            </div>

            <div className="shrink-0">
              <div className="bg-app-panel inline-flex h-[46px] w-[206px] items-center gap-[10px] rounded-2xl px-3 py-3">
                <span className="h-4 w-4 rounded-full border border-[#8f8f8f]" />
                <span className="truncate text-base leading-5 font-medium text-black">
                  {summaryLabel}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {order.items.map((item) => {
              const currentStatus =
                itemStatuses[item.id] ?? DEFAULT_ITEM_STATUS;
              const isCanceled = currentStatus === 'Отменен';
              const itemTrack = trackNumbers[item.id] ?? '';

              return (
                <div
                  key={item.id}
                  className="grid grid-cols-[64px_minmax(0,1fr)] items-start gap-4 sm:grid-cols-[64px_246px_80px_minmax(0,1fr)]"
                >
                  <div>
                    <Image
                      src={item.image}
                      alt={item.title}
                      width={64}
                      height={64}
                      className="rounded"
                    />
                  </div>

                  <div>
                    <p className="h-10 overflow-hidden text-base leading-5 font-medium text-black">
                      {item.title}
                    </p>
                    <p className="text-app-muted mt-1 text-base leading-5 font-medium">
                      Размер: {item.size}
                    </p>
                  </div>

                  <p className="text-app-text-dark text-left text-base leading-5 font-medium sm:mt-[22px]">
                    {formatCurrency(item.price)}
                  </p>

                  <div className="flex items-center justify-end gap-2">
                    {!isCanceled && (
                      <div
                        className={cn(
                          'flex h-[38px] min-w-[220px] items-center gap-2 rounded-xl px-4',
                          itemTrack ? 'bg-[#d9d9d9]' : 'bg-app-panel',
                        )}
                      >
                        <input
                          value={itemTrack}
                          onChange={(event) =>
                            setTrackNumbers((prev) => ({
                              ...prev,
                              [item.id]: event.target.value,
                            }))
                          }
                          placeholder="Китайский трек-номер"
                          className="text-app-text-dark h-5 w-full bg-transparent p-0 text-base leading-5 font-medium outline-none placeholder:text-[#8e8e8e]"
                        />
                        {itemTrack && (
                          <button
                            type="button"
                            onClick={() =>
                              setTrackNumbers((prev) => ({
                                ...prev,
                                [item.id]: '',
                              }))
                            }
                            className="text-app-text-dark text-2xl leading-none"
                            aria-label="Очистить трек-номер"
                          >
                            ×
                          </button>
                        )}
                      </div>
                    )}

                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => {
                          if (!isCanceled)
                            setMenuItemId((prev) =>
                              prev === item.id ? null : item.id,
                            );
                        }}
                        className={cn(
                          'text-app-text-dark inline-flex h-[38px] items-center gap-2 rounded-xl px-4 text-base leading-5 font-medium',
                          isCanceled ? 'bg-[#cfcfcf]' : 'bg-app-panel',
                        )}
                      >
                        {!isCanceled && (
                          <span className="h-4 w-4 rounded-full border border-[#8f8f8f]" />
                        )}
                        <span>{currentStatus}</span>
                        {!isCanceled && (
                          <ChevronIcon className="h-4 w-4 text-[#8a8a8a]" />
                        )}
                      </button>

                      {menuItemId === item.id && !isCanceled && (
                        <div className="bg-app-panel shadow-soft absolute top-[calc(100%+14px)] right-0 z-20 h-[190px] w-[277px] overflow-hidden rounded-2xl py-2">
                          {STATUS_OPTIONS.map((option) => (
                            <StatusMenuButton
                              key={option}
                              label={option}
                              selected={option === currentStatus}
                              onClick={() => {
                                setItemStatuses((prev) => ({
                                  ...prev,
                                  [item.id]: option,
                                }));
                                setMenuItemId(null);
                              }}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 h-px bg-[#dbd9d6]" />

          <div className="mt-2.5 flex items-center justify-between">
            <p className="text-app-text-dark text-[34px] leading-[38px] font-bold tracking-[-0.5px]">
              Итого
            </p>
            <p className="text-[40px] leading-[42px] font-bold tracking-[-0.4px] text-[#111111]">
              {formatCurrency(order.total)}
            </p>
          </div>
        </div>

        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={handleSave}
            className="bg-app-text-dark inline-flex h-[46px] w-[213px] items-center justify-center rounded-2xl px-3 py-3 text-base leading-5 font-medium text-white opacity-60"
          >
            Сохранить изменения
          </button>
        </div>
      </div>
    </Modal>
  );
}
