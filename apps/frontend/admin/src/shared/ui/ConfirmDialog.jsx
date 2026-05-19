'use client';

import { useEffect, useRef } from 'react';

import { Button } from './Button';
import { Modal } from './Modal';

/**
 * Styled, themable replacement for `window.confirm()`. Reuses the project's
 * Modal shell so focus trapping, Esc-to-close, body scroll lock and aria
 * plumbing come for free.
 *
 * Use for destructive / undoable actions (revoke invitation, delete role,
 * cancel order, etc.) — anywhere we previously fell back to a native
 * browser prompt that breaks our visual language and accessibility story.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Подтвердить',
  cancelLabel = 'Отмена',
  variant = 'danger',
  onConfirm,
  onClose,
  pending = false,
}) {
  const confirmRef = useRef(null);

  // Default focus to the *cancel* button on destructive dialogs (operator
  // shouldn't be able to fly through with Enter and irrevocably delete
  // something). For neutral confirms (variant='neutral'), default to the
  // primary action — that's the expected flow.
  useEffect(() => {
    if (!open) return;
    if (variant === 'neutral') return; // primary already gets autofocus via Modal
    const id = requestAnimationFrame(() => {
      confirmRef.current?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(id);
  }, [open, variant]);

  return (
    <Modal
      open={open}
      onClose={pending ? () => {} : onClose}
      title={title}
      size="sm"
    >
      {description && (
        <p className="text-app-muted mt-3 text-sm leading-5">{description}</p>
      )}
      <div className="mt-5 flex justify-end gap-2">
        <Button
          variant="secondary"
          onClick={onClose}
          disabled={pending}
          ref={variant === 'danger' ? confirmRef : null}
        >
          {cancelLabel}
        </Button>
        <Button
          variant={variant === 'danger' ? 'danger' : 'primary'}
          onClick={onConfirm}
          disabled={pending}
        >
          {pending ? 'Выполняется…' : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
