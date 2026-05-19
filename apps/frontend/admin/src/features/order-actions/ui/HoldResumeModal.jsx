'use client';

import { useEffect, useState } from 'react';
import { Modal } from '@/shared/ui/Modal';
import { cn, formatDateTime } from '@/shared/lib/utils';
import { HOLD_REASONS_FOR_ADMIN, HOLD_REASON_LABELS } from '@/entities/order';
import { useHoldOrder, useResumeOrder } from '../model/useOrderActions';

const HOLD_DURATION_DAYS = 30;

export function HoldResumeModal({ open, onClose, order, mode = 'hold' }) {
  const isResume = mode === 'resume';
  const [reason, setReason] = useState('');

  const holdMutation = useHoldOrder(order?.orderId);
  const resumeMutation = useResumeOrder(order?.orderId);
  const mutation = isResume ? resumeMutation : holdMutation;

  useEffect(() => {
    if (open) {
      setReason('');
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, order?.orderId, mode]);

  if (!order) return null;

  const isValid = isResume || HOLD_REASONS_FOR_ADMIN.includes(reason);
  const previewUntil = new Date();
  previewUntil.setDate(previewUntil.getDate() + HOLD_DURATION_DAYS);

  const submit = (e) => {
    e.preventDefault();
    if (mutation.isPending || !isValid) return;
    if (isResume) {
      resumeMutation.mutate(undefined, { onSuccess: onClose });
    } else {
      holdMutation.mutate({ reason }, { onSuccess: onClose });
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="sm"
      title={isResume ? 'Возобновить заказ' : 'Поставить на hold'}
    >
      <form onSubmit={submit} className="mt-4 space-y-4">
        {isResume ? (
          <p className="text-app-text-dark text-sm">
            Заказ вернётся в статус{' '}
            <code className="bg-app-card rounded px-1.5 py-0.5">
              {order.preHoldStatus ?? '—'}
            </code>
            . Hold-причина будет очищена.
          </p>
        ) : (
          <>
            <fieldset className="space-y-2">
              <legend className="text-app-text-dark mb-1 block text-sm font-medium">
                Причина hold-а
              </legend>
              <p className="text-app-muted mb-2 text-xs">
                Один из заранее заданных кодов — backend принимает только
                значения enum-а.
              </p>
              <div
                role="radiogroup"
                aria-label="Причина hold-а"
                className="grid grid-cols-1 gap-2"
              >
                {HOLD_REASONS_FOR_ADMIN.map((value) => {
                  const checked = reason === value;
                  return (
                    <label
                      key={value}
                      className={cn(
                        'border-app-border flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2 text-sm transition-colors',
                        checked
                          ? 'border-app-text-dark bg-app-card'
                          : 'hover:border-app-text-dark/40',
                      )}
                    >
                      <input
                        type="radio"
                        name="holdReason"
                        value={value}
                        checked={checked}
                        onChange={() => setReason(value)}
                        disabled={mutation.isPending}
                        className="mt-0.5"
                      />
                      <span>
                        <span className="text-app-text-dark block font-medium">
                          {HOLD_REASON_LABELS[value]}
                        </span>
                        <code className="text-app-muted text-[11px]">
                          {value}
                        </code>
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            <div className="bg-app-card rounded-lg p-3 text-xs">
              <p className="text-app-muted">
                Hold по умолчанию длится {HOLD_DURATION_DAYS} дней. Будет
                автоматически снят примерно{' '}
                <span className="text-app-text-dark font-medium">
                  {formatDateTime(previewUntil.toISOString())}
                </span>
                , если admin не возобновит вручную.
              </p>
            </div>
          </>
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
            className={cn(
              'rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50',
              isResume ? 'bg-app-success' : 'bg-orange-600',
            )}
          >
            {mutation.isPending
              ? 'Сохраняем…'
              : isResume
                ? 'Возобновить'
                : 'Поставить на hold'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
