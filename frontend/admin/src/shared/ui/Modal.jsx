'use client';

import { useId } from 'react';
import { useBodyScrollLock } from '@/shared/hooks/useBodyScrollLock';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { cn } from '@/shared/lib/utils';

const SIZE_CLASSES = {
  sm: 'max-w-[380px]',
  md: 'max-w-[460px]',
  lg: 'max-w-[640px]',
  xl: 'max-w-[820px]',
  '2xl': 'max-w-[1040px]',
  full: 'max-w-[min(1200px,calc(100vw-2rem))]',
};

/**
 * Generic modal shell:
 *   - locks body scroll while open
 *   - closes on Esc and overlay click
 *   - sets aria-modal + aria-labelledby plumbing
 *
 * Children render the modal body. The dialog itself is unstyled padding-wise
 * so callers can decide content layout.
 */
export function Modal({
  open,
  onClose,
  title,
  titleId: titleIdProp,
  children,
  size = 'md',
  className,
  overlayClassName,
  contentClassName,
  hidePadding = false,
  closeOnOverlayClick = true,
}) {
  const generatedId = useId();
  const titleId = titleIdProp || `modal-title-${generatedId}`;

  useBodyScrollLock(open);
  useEscapeKey(onClose, open);

  if (!open) return null;

  return (
    <div
      className={cn(
        'fixed inset-0 z-90 flex items-center justify-center bg-black/40 p-4',
        overlayClassName,
      )}
      role="presentation"
      onClick={closeOnOverlayClick ? onClose : undefined}
    >
      <div
        className={cn(
          'bg-app-panel shadow-soft w-full rounded-3xl',
          SIZE_CLASSES[size] ?? SIZE_CLASSES.md,
          !hidePadding && 'p-6',
          className,
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        {title && (
          <p
            id={titleId}
            className={cn(
              'text-app-text m-0 text-2xl leading-[30px] font-bold',
              hidePadding && 'px-6 pt-6',
            )}
          >
            {title}
          </p>
        )}
        {contentClassName ? (
          <div className={contentClassName}>{children}</div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
