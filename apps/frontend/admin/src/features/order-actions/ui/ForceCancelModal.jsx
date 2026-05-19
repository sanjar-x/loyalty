'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Modal } from '@/shared/ui/Modal';
import { cn } from '@/shared/lib/utils';
import {
  CANCELLATION_CATEGORY_LABELS,
  cancellationReasonLabel,
  useCancellationReasons,
} from '@/entities/order';
import {
  generateIdempotencyKey,
  useForceCancelOrder,
} from '../model/useOrderActions';

function inferWasPaid(order) {
  // Best-effort proxy until backend exposes `wasPaid` directly: any order
  // that ever held a PaymentIntent is assumed to have charged the user. The
  // detail page header already shows raw status, so an over-cautious refund
  // warning is preferable to silently missing a chargeback case.
  if (!order) return false;
  if (order.paymentIntentId) return true;
  return [
    'paid',
    'procured',
    'arrived_in_ru',
    'in_last_mile',
    'ready_for_pickup',
    'delivered',
  ].includes(order.status);
}

/**
 * Backend returns the categories in domain order (customer / merchant /
 * system / logistics). The grouped dropdown renders them as section
 * headers with the localized label and indents reasons underneath.
 *
 * `query` is matched against the localized label, the raw enum code, and
 * the category label so the admin can search either ru text or the
 * `customer_*` / `merchant_*` prefix.
 */
function filterGroups(groups, query) {
  if (!query) return groups;
  const q = query.trim().toLowerCase();
  if (!q) return groups;
  return groups
    .map((group) => {
      const categoryLabel =
        CANCELLATION_CATEGORY_LABELS[group.code] ?? group.code;
      const reasons = group.reasons.filter(
        (code) =>
          code.toLowerCase().includes(q) ||
          cancellationReasonLabel(code).toLowerCase().includes(q) ||
          categoryLabel.toLowerCase().includes(q),
      );
      return reasons.length ? { ...group, reasons } : null;
    })
    .filter(Boolean);
}

export function ForceCancelModal({ open, onClose, order, onSuccess }) {
  const [reasonValue, setReasonValue] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [query, setQuery] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const pickerRef = useRef(null);

  const mutation = useForceCancelOrder(order?.orderId);
  const reasonsQuery = useCancellationReasons();
  const groups = useMemo(
    () => reasonsQuery.data?.categories ?? [],
    [reasonsQuery.data],
  );

  // Reset form on (re)open. Idempotency key is frozen per attempt so a
  // backend retry cannot duplicate the cancellation.
  useEffect(() => {
    if (open) {
      setIdempotencyKey(generateIdempotencyKey());
      setReasonValue('');
      setQuery('');
      setPickerOpen(false);
      setActiveIndex(0);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, order?.orderId]);

  // Close the picker on outside click — replicates the behaviour of the
  // shared <DropdownPill> without dragging in shared/ui dependencies.
  useEffect(() => {
    if (!pickerOpen) return undefined;
    function handleMouseDown(event) {
      if (!pickerRef.current?.contains(event.target)) setPickerOpen(false);
    }
    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, [pickerOpen]);

  const filteredGroups = useMemo(
    () => filterGroups(groups, query),
    [groups, query],
  );

  // Flat list of selectable codes — used for keyboard navigation indices.
  const flatCodes = useMemo(
    () => filteredGroups.flatMap((g) => g.reasons),
    [filteredGroups],
  );

  // Keep the highlighted row in range when the filter shrinks the list.
  useEffect(() => {
    setActiveIndex((prev) => {
      if (flatCodes.length === 0) return 0;
      return Math.min(prev, flatCodes.length - 1);
    });
  }, [flatCodes.length]);

  const wasPaid = useMemo(() => inferWasPaid(order), [order]);

  if (!order) return null;

  const isValid = reasonValue.length > 0;

  const submit = (e) => {
    e.preventDefault();
    if (!isValid || mutation.isPending) return;
    mutation.mutate(
      { reason: reasonValue, idempotencyKey },
      {
        onSuccess: () => {
          onSuccess?.();
          onClose();
        },
      },
    );
  };

  function pickReason(code) {
    setReasonValue(code);
    setQuery('');
    setPickerOpen(false);
  }

  function handleKeyDown(e) {
    if (!pickerOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setPickerOpen(true);
      }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, flatCodes.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const code = flatCodes[activeIndex];
      if (code) pickReason(code);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setPickerOpen(false);
    }
  }

  const buttonLabel = reasonValue
    ? cancellationReasonLabel(reasonValue)
    : 'Выберите причину…';

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title="Принудительная отмена"
    >
      <form onSubmit={submit} className="mt-4 space-y-4">
        {wasPaid && (
          <div
            role="alert"
            className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800"
          >
            Заказ оплачен. Backend инициирует возврат средств — это может занять
            несколько минут.
          </div>
        )}

        <div ref={pickerRef} className="relative">
          <label
            htmlFor="cancel-reason-trigger"
            className="text-app-text-dark mb-1 block text-sm font-medium"
          >
            Причина
          </label>
          <button
            id="cancel-reason-trigger"
            type="button"
            onClick={() => setPickerOpen((v) => !v)}
            onKeyDown={handleKeyDown}
            aria-haspopup="listbox"
            aria-expanded={pickerOpen}
            disabled={reasonsQuery.isPending && !reasonsQuery.data}
            className={cn(
              'border-app-border focus:border-app-text-dark flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition-colors outline-none',
              reasonValue ? 'text-app-text-dark' : 'text-app-muted',
              reasonsQuery.isError && 'border-app-danger',
            )}
          >
            <span className="truncate">
              {reasonsQuery.isPending && !reasonsQuery.data
                ? 'Загружаем причины…'
                : buttonLabel}
            </span>
            <span aria-hidden="true" className="text-app-muted ml-2 text-xs">
              ▾
            </span>
          </button>

          {reasonsQuery.isError && (
            <p role="alert" className="text-app-danger mt-1 text-xs">
              Не удалось загрузить причины. Перезагрузите модальное окно.
            </p>
          )}

          {pickerOpen && (
            <div
              role="listbox"
              aria-label="Причины отмены"
              className="border-app-border bg-app-panel absolute z-10 mt-1 max-h-80 w-full overflow-auto rounded-lg border shadow-lg"
            >
              <div className="border-app-border bg-app-panel sticky top-0 border-b p-2">
                <input
                  type="search"
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Поиск (ru/код)…"
                  aria-label="Поиск причины отмены"
                  className="border-app-border focus:border-app-text-dark w-full rounded-md border px-2 py-1.5 text-sm outline-none"
                />
              </div>
              {filteredGroups.length === 0 ? (
                <p className="text-app-muted px-3 py-4 text-center text-xs">
                  Ничего не найдено
                </p>
              ) : (
                filteredGroups.map((group) => (
                  <CategorySection
                    key={group.code}
                    group={group}
                    activeCode={flatCodes[activeIndex]}
                    selectedCode={reasonValue}
                    onPick={pickReason}
                  />
                ))
              )}
            </div>
          )}
        </div>

        {reasonValue && idempotencyKey && (
          <p className="text-app-muted text-xs">
            idempotency-key зафиксирован для этой попытки:{' '}
            <code className="bg-app-card rounded px-1 font-mono">
              {idempotencyKey.slice(0, 8)}…
            </code>
          </p>
        )}

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
            type="submit"
            disabled={!isValid || mutation.isPending}
            className="bg-app-danger rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? 'Отменяем…' : 'Принудительная отмена'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CategorySection({ group, activeCode, selectedCode, onPick }) {
  const label = CANCELLATION_CATEGORY_LABELS[group.code] ?? group.code;
  return (
    <div role="group" aria-label={label}>
      <p className="text-app-muted bg-app-card sticky top-[44px] px-3 py-1 text-[11px] font-semibold tracking-wide uppercase">
        {label}
      </p>
      <ul className="py-1">
        {group.reasons.map((code) => {
          const active = code === activeCode;
          const selected = code === selectedCode;
          return (
            <li
              key={code}
              role="option"
              aria-selected={selected}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onPick(code)}
              className={cn(
                'flex cursor-pointer items-baseline justify-between px-3 py-1.5 text-sm transition-colors',
                active && 'bg-app-card',
                selected && 'text-app-text-dark font-medium',
              )}
            >
              <span>{cancellationReasonLabel(code)}</span>
              <code className="text-app-muted ml-3 text-[11px]">{code}</code>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
