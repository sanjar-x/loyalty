'use client';

import { useEffect, useMemo, useState } from 'react';
import { Modal } from '@/shared/ui/Modal';
import { cn } from '@/shared/lib/utils';
import {
  INCOMING_DECLARATION_RE,
  validateIncomingDeclaration,
} from '@/entities/order';
import { useProcureOrder } from '../model/useOrderActions';

// Maps backend error_code → modal-specific copy. Only codes whose meaning is
// distinct enough to warrant a custom message are listed; anything else
// falls through to `err.message` (already translated by the api-client
// translation map for ORDER_* codes).
const ERROR_OVERRIDES = {
  ORDER_INVALID_TRANSITION:
    'Заказ уже не в статусе «Оплачен» — обновите страницу.',
  MEDIA_PROCESSING_TIMEOUT:
    'Сервер не успел подтвердить операцию. Проверьте через минуту, не повторился ли заказ.',
};

export function ProcureModal({ open, onClose, order, onSuccess }) {
  const [value, setValue] = useState('');
  const [touched, setTouched] = useState(false);
  const mutation = useProcureOrder(order?.orderId);

  // Reset form on every (re)open so a previous failed attempt doesn't
  // leak into a fresh session for a different order.
  useEffect(() => {
    if (open) {
      setValue('');
      setTouched(false);
      mutation.reset();
    }
    // intentionally do not depend on `mutation` — its identity is stable
    // across renders only by react-query's design and adding it would
    // create a reset loop on every fetch transition.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, order?.orderId]);

  const trimmed = value.trim();
  const isValid = trimmed.length > 0 && validateIncomingDeclaration(trimmed);
  const showInlineError = touched && trimmed.length > 0 && !isValid;

  const errorMessage = useMemo(() => {
    if (!mutation.error) return null;
    const code = mutation.error?.code;
    return ERROR_OVERRIDES[code] ?? mutation.error.message;
  }, [mutation.error]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setTouched(true);
    if (!isValid || mutation.isPending) return;
    mutation.mutate(
      { incomingDeclaration: trimmed },
      {
        onSuccess: () => {
          onSuccess?.();
          onClose();
        },
      },
    );
  };

  if (!order) return null;

  return (
    <Modal open={open} onClose={onClose} size="sm" title="Передать в закупку">
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label
            htmlFor="incomingDeclaration"
            className="text-app-text-dark mb-1 block text-sm font-medium"
          >
            Incoming declaration (китайская декларация)
          </label>
          <input
            id="incomingDeclaration"
            type="text"
            autoComplete="off"
            spellCheck={false}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => setTouched(true)}
            disabled={mutation.isPending}
            placeholder="Например: CN-12-AB-9876"
            aria-invalid={showInlineError || undefined}
            className={cn(
              'border-app-border focus:border-app-text-dark w-full rounded-lg border px-3 py-2 font-mono text-sm transition-colors outline-none',
              showInlineError && 'border-app-danger',
            )}
          />
          <p
            className={cn(
              'mt-1 text-xs',
              showInlineError ? 'text-app-danger' : 'text-app-muted',
            )}
          >
            Латинские буквы, цифры и дефис, до 15 символов. Шаблон:{' '}
            <code className="font-mono">{INCOMING_DECLARATION_RE.source}</code>.
          </p>
        </div>

        {errorMessage && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {errorMessage}
          </div>
        )}

        <p className="text-app-muted bg-app-card rounded-lg p-3 text-xs">
          После сохранения backend забронирует cross-border отправку у
          DobroPost. Booking асинхронный — статус заказа обновится через
          несколько секунд.
        </p>

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
            className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? 'Сохраняем…' : 'Передать в закупку'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
