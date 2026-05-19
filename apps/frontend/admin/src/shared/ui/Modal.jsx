'use client';

import { useEffect, useId, useRef } from 'react';
import { useBodyScrollLock } from '@/shared/hooks/useBodyScrollLock';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { cn } from '@/shared/lib/utils';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function getFocusable(root) {
  if (!root) return [];
  // Don't gate on `offsetParent !== null` — that filter would catch
  // visually-hidden elements but jsdom never reports a layout, so it
  // would also strip every node during component tests. Browsers
  // already won't focus `display:none` content; leave that to them.
  return Array.from(root.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute('aria-hidden'),
  );
}

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
  const dialogRef = useRef(null);
  const previousFocusRef = useRef(null);

  useBodyScrollLock(open);
  useEscapeKey(onClose, open);

  /**
   * Audit 1.5 + 1.6: keyboard accessibility.
   *
   *   - On open: snapshot the trigger element, autofocus the first
   *     focusable element inside the dialog so Tab navigation begins
   *     within the modal.
   *   - On Tab: cycle focus inside the dialog (Tab from last → first,
   *     Shift+Tab from first → last).
   *   - On close: return focus to the original trigger so keyboard /
   *     screen-reader users don't lose orientation.
   *
   * The effect runs in a single useEffect keyed on `open` so all three
   * concerns share one teardown — easier to reason about than three
   * effects with overlapping dependencies.
   */
  useEffect(() => {
    if (!open) return undefined;

    const dialog = dialogRef.current;
    previousFocusRef.current =
      typeof document !== 'undefined' ? document.activeElement : null;

    // Defer the autofocus by one frame so portaled-in content (custom
    // children that mount on first render) finishes rendering before
    // we try to focus the first interactive element.
    const focusFrame = requestAnimationFrame(() => {
      const focusables = getFocusable(dialog);
      if (focusables.length > 0) {
        focusables[0].focus();
      } else if (dialog) {
        // Empty dialogs (preview / loading state) — focus the dialog
        // itself so Esc still works without a stale outside focus.
        dialog.tabIndex = -1;
        dialog.focus();
      }
    });

    function handleKeyDown(event) {
      if (event.key !== 'Tab' || !dialog) return;
      const focusables = getFocusable(dialog);
      if (focusables.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !dialog.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      cancelAnimationFrame(focusFrame);
      document.removeEventListener('keydown', handleKeyDown);
      // Return focus to whoever opened the modal.
      const previous = previousFocusRef.current;
      if (previous && typeof previous.focus === 'function') {
        previous.focus();
      }
      previousFocusRef.current = null;
    };
  }, [open]);

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
        ref={dialogRef}
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
