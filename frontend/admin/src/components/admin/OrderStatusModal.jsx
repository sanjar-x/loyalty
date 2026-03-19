'use client';

import Image from 'next/image';
import { useCallback, useEffect, useRef, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import { CopyMark } from '@/components/ui/CopyMark';
import { cn, formatCurrency, formatDateTime } from '@/lib/utils';

const statusOptions = ['Оформлен', 'В пути', 'Отменен'];

function StatusMenuButton({ label, selected, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-[16px] font-medium leading-5 text-[#000000] hover:bg-[#f4f4f4]"
    >
      <span className="inline-flex items-center gap-2">
        {label !== 'Отменен' ? <span className="h-4 w-4 rounded-full border border-[#7f7f7f]" /> : <span className="w-4" />}
        {label}
      </span>
      <span
        className={cn(
          'inline-flex h-5 w-5 items-center justify-center rounded-full text-[12px] leading-none',
          selected ? 'bg-[#2d2d2d] text-white' : 'bg-[#ececec] text-transparent',
        )}
      >
        ✓
      </span>
    </button>
  );
}

export function OrderStatusModal({ open, order, onClose, onSave, initialItemStatuses, initialTrackNumbers }) {
  const [trackNumbers, setTrackNumbers] = useState({});
  const [itemStatuses, setItemStatuses] = useState({});
  const [menuItemId, setMenuItemId] = useState(null);
  const modalRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open || !order) return;

    const initial = {};
    const initialTracks = {};
    order.items.forEach((item) => {
      initial[item.id] = initialItemStatuses?.[item.id] ?? 'Оформлен';
      initialTracks[item.id] = initialTrackNumbers?.[item.id] ?? '';
    });
    setItemStatuses(initial);
    setTrackNumbers(initialTracks);
    setMenuItemId(null);
  }, [open, order, initialItemStatuses, initialTrackNumbers]);

  useEffect(() => {
    if (!open) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function handleKeyDown(event) {
      if (event.key === 'Escape') onCloseRef.current();
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;

    function handleClickOutside(event) {
      const target = event.target;
      if (!modalRef.current) return;
      if (typeof Node !== 'undefined' && target instanceof Node && modalRef.current.contains(target)) return;
      onCloseRef.current();
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  if (!open || !order) return null;

  const completedCount = Object.values(itemStatuses).filter((status) => status === 'Оформлен').length;
  const summaryLabel = order.items.length > 1 ? `Оформлен ${completedCount} из ${order.items.length}` : 'Оформлен';
  const handleSave = () => {
    onSave({ orderId: order.id, itemStatuses, trackNumbers });
    onCloseRef.current();
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/55 p-3 md:p-4">
      <div
        ref={modalRef}
        className="relative w-[1380px] max-h-[calc(100vh-24px)] max-w-[calc(100vw-24px)] overflow-y-auto rounded-[20px] bg-[#f4f3f1] px-6 pb-5 pt-5"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[26px] font-bold leading-8 tracking-[-0.42px] text-[#3a3a3a]">Изменить статус</h2>
          <button type="button" onClick={onClose} className="relative h-6 w-6" aria-label="Закрыть">
            <span className="absolute left-1/2 top-1/2 h-[3px] w-4 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-[#000000]" />
            <span className="absolute left-1/2 top-1/2 h-[3px] w-4 -translate-x-1/2 -translate-y-1/2 -rotate-45 bg-[#000000]" />
          </button>
        </div>

        <div className="rounded-[16px] bg-[#efeeec] px-5 py-4">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2 text-base font-medium leading-5 text-[#7e7e7e]">
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
                <span className="ml-1 rounded-full bg-[#f2e5c2] px-3 py-1 text-sm font-medium leading-5 text-[#5c4a17]">Из Китая</span>
              )}
              <span className="rounded-full bg-[#2f2f2f] px-3 py-1 text-sm font-medium leading-5 text-white">Оригинал</span>
            </div>

            <div className="shrink-0">
              <div className="inline-flex h-[46px] w-[206px] items-center gap-[10px] rounded-[15px] bg-white px-[13px] py-3">
                <span className="h-4 w-4 rounded-full border border-[#8f8f8f]" />
                <span className="truncate text-base font-medium leading-5 text-[#000000]">{summaryLabel}</span>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {order.items.map((item) => {
              const currentStatus = itemStatuses[item.id] ?? 'Оформлен';
              const isCanceled = currentStatus === 'Отменен';
              const itemTrack = trackNumbers[item.id] ?? '';

              return (
                <div
                  key={item.id}
                  className="grid items-start gap-4 grid-cols-[64px_minmax(0,1fr)] sm:grid-cols-[64px_246px_80px_minmax(0,1fr)]"
                >
                  <div>
                    <Image src={item.image} alt={item.title} width={64} height={64} className="rounded" />
                  </div>

                  <div>
                    <p className="h-[40px] overflow-hidden text-[16px] font-medium leading-5 text-[#000000]">{item.title}</p>
                    <p className="mt-1 text-base font-medium leading-5 text-[#7e7e7e]">Размер: {item.size}</p>
                  </div>

                  <p className="text-left text-[16px] font-medium leading-5 text-[#2d2d2d] sm:mt-[22px]">{formatCurrency(item.price)}</p>

                  <div className="flex items-center justify-end gap-2">
                    {!isCanceled && (
                      <div className={cn('flex h-[38px] min-w-[220px] items-center gap-2 rounded-[12px] px-4', itemTrack ? 'bg-[#d9d9d9]' : 'bg-white')}>
                        <input
                          value={itemTrack}
                          onChange={(event) => setTrackNumbers((prev) => ({ ...prev, [item.id]: event.target.value }))}
                          placeholder="Китайский трек-номер"
                          className="h-5 w-full bg-transparent p-0 text-base font-medium leading-5 text-[#2d2d2d] outline-none placeholder:text-[#8e8e8e]"
                        />
                        {itemTrack && (
                          <button
                            type="button"
                            onClick={() => setTrackNumbers((prev) => ({ ...prev, [item.id]: '' }))}
                            className="text-2xl leading-none text-[#2d2d2d]"
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
                        onClick={() => { if (!isCanceled) setMenuItemId((prev) => (prev === item.id ? null : item.id)); }}
                        className={cn(
                          'inline-flex h-[38px] items-center gap-2 rounded-[12px] px-4 text-base font-medium leading-5 text-[#2d2d2d]',
                          isCanceled ? 'bg-[#cfcfcf]' : 'bg-white',
                        )}
                      >
                        {!isCanceled && <span className="h-4 w-4 rounded-full border border-[#8f8f8f]" />}
                        <span>{currentStatus}</span>
                        {!isCanceled && <ChevronIcon className="h-4 w-4 text-[#8a8a8a]" />}
                      </button>

                      {menuItemId === item.id && !isCanceled && (
                        <div className="absolute right-0 top-[calc(100%+14px)] z-20 h-[190px] w-[277px] overflow-hidden rounded-[20px] bg-white py-2 shadow-[0_12px_26px_rgba(22,22,22,0.16)]">
                          {statusOptions.map((option) => (
                            <StatusMenuButton
                              key={option}
                              label={option}
                              selected={option === currentStatus}
                              onClick={() => {
                                setItemStatuses((prev) => ({ ...prev, [item.id]: option }));
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
            <p className="text-[34px] font-bold leading-[38px] tracking-[-0.5px] text-[#2d2d2d]">Итого</p>
            <p className="text-[40px] font-bold leading-[42px] tracking-[-0.4px] text-[#111111]">{formatCurrency(order.total)}</p>
          </div>
        </div>

        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={handleSave}
            className="inline-flex h-[46px] w-[213px] items-center justify-center rounded-[15px] bg-[#2d2d2d] px-[13px] py-3 text-[16px] font-medium leading-5 text-white opacity-60"
          >
            Сохранить изменения
          </button>
        </div>
      </div>
    </div>
  );
}
