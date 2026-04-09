'use client';

import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from 'react';

import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ANIMATION_MS = 240;
const UNMOUNT_DELAY_MS = ANIMATION_MS + 30;
const EASING = 'cubic-bezier(0.22, 1, 0.36, 1)';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type BottomSheetVariant = 'default' | 'fullscreen' | 'filter' | 'review' | 'module';

interface BottomSheetProps {
  /** Controls which visual mode the sheet renders in. */
  variant?: BottomSheetVariant;
  /** Whether the sheet is open. */
  open: boolean;
  /** Called when the user requests to close (backdrop click, Escape, close button). */
  onClose: () => void;
  /** Optional title rendered in the default header. */
  title?: string;
  /** Accessible label when no visible title is provided. */
  ariaLabel?: string;
  /** Replaces the entire default header when provided. */
  header?: ReactNode;
  /** Main scrollable content. */
  children: ReactNode;
  /** Sticky footer area below the scrollable body. */
  footer?: ReactNode;
  /**
   * Pixel offset subtracted from the Telegram viewport height to compute
   * the sheet max-height. Defaults to 24.
   */
  maxHeightOffset?: number;
  /** Ref to the element that should receive focus when the sheet opens. */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** Additional className merged onto the outermost wrapper. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BottomSheet({
  variant = 'default',
  open,
  onClose,
  title,
  ariaLabel,
  header,
  children,
  footer,
  maxHeightOffset = 24,
  initialFocusRef,
  className,
}: BottomSheetProps) {
  const [mounted, setMounted] = useState(open);
  const [active, setActive] = useState(false);
  const titleId = useId();
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);

  // Keep onClose ref in sync without re-running effects.
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // ---------- Mount / unmount with animation ---------
  useEffect(() => {
    let frame1 = 0;
    let frame2 = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    if (open) {
      frame1 = requestAnimationFrame(() => {
        setMounted(true);
        setActive(false);
        frame2 = requestAnimationFrame(() => setActive(true));
      });
    } else {
      frame1 = requestAnimationFrame(() => setActive(false));
      timer = setTimeout(() => setMounted(false), UNMOUNT_DELAY_MS);
    }

    return () => {
      if (frame1) cancelAnimationFrame(frame1);
      if (frame2) cancelAnimationFrame(frame2);
      if (timer) clearTimeout(timer);
    };
  }, [open]);

  // ---------- Body scroll lock, Escape key, focus management ----------
  useEffect(() => {
    if (!mounted) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current?.();
    };

    window.addEventListener('keydown', onKeyDown);

    if (open) {
      const el = initialFocusRef?.current ?? closeBtnRef.current;
      if (el && document.activeElement !== el) el.focus?.();
    }

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [initialFocusRef, mounted, open]);

  if (!mounted) return null;

  // ---------- Variant-derived flags ----------
  const isFilter = variant === 'filter';
  const isFullscreen = variant === 'fullscreen';
  const isModule = variant === 'module';
  const isReview = variant === 'review';

  // ---------- Computed inline styles ----------
  const sheetWrapMinHeight = isFilter || isFullscreen ? '100dvh' : isModule ? '80vh' : 'auto';

  const sheetStyle: React.CSSProperties =
    isFilter || isFullscreen
      ? {}
      : {
          maxHeight: `min(85vh, calc(var(--tg-viewport-stable-height, 100vh) - ${maxHeightOffset}px))`,
          height: isReview
            ? 'auto'
            : `min(85vh, calc(var(--tg-viewport-stable-height, 100vh) - ${maxHeightOffset}px))`,
        };

  const bodyMaxHeight: string | undefined =
    isFilter || isFullscreen ? undefined : isReview ? undefined : '446px';

  // ---------- Render ----------
  const sheet = (
    <div
      className={cn(
        'fixed inset-0 z-60 mx-auto flex max-w-[448px] justify-center',
        isFilter || isFullscreen ? 'max-w-none items-stretch' : 'items-end',
        className,
      )}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title && !ariaLabel ? titleId : undefined}
      aria-label={!title && ariaLabel ? ariaLabel : undefined}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Backdrop */}
      <div
        className={cn(
          'absolute inset-0 bg-black/56 will-change-[opacity]',
          active ? 'opacity-100' : 'opacity-0',
        )}
        style={{ transition: `opacity ${ANIMATION_MS}ms ${EASING}` }}
        onClick={onClose}
      />

      {/* Sheet wrapper — handles the slide-up transform */}
      <div
        className={cn(
          'relative w-full will-change-transform',
          active ? 'translate-y-0' : 'translate-y-full',
        )}
        style={{
          transition: `transform ${ANIMATION_MS}ms ${EASING}`,
          minHeight: sheetWrapMinHeight,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sheet panel */}
        <div
          className={cn(
            'relative flex w-full flex-col overflow-hidden bg-white shadow-[0_0_40px_0_rgba(0,0,0,0.15)]',
            isFilter || isFullscreen
              ? 'h-dvh max-h-dvh rounded-none pt-[calc(var(--tg-safe-area-top,0px)+24px)]'
              : 'rounded-t-[22px]',
            isModule && 'max-h-[90vh]',
          )}
          style={sheetStyle}
        >
          {/* Grabber handle */}
          {!(isFilter || isFullscreen) && (
            <div
              className="absolute top-2.5 left-1/2 h-1 w-9 -translate-x-1/2 rounded-full bg-black/12"
              aria-hidden="true"
            />
          )}

          {/* Header */}
          {header ? (
            header
          ) : (
            <header className="relative flex items-start justify-between gap-3 px-4 pt-[25px]">
              {title ? (
                <h2
                  id={titleId}
                  className={cn(
                    'm-0 text-xl leading-[1.2] font-bold tracking-tight text-black',
                    (isFilter || isFullscreen) &&
                      'fixed inset-x-0 top-0 z-10 block bg-white pt-[calc(var(--tg-safe-area-top,0px)+16px)] pb-2.5 text-center text-[15px] font-medium',
                  )}
                >
                  {title}
                </h2>
              ) : (
                <div />
              )}

              {!(isFilter || isFullscreen) && (
                <button
                  ref={closeBtnRef}
                  type="button"
                  aria-label="Закрыть"
                  onClick={onClose}
                  className="absolute top-4 right-[17px] grid h-7 w-7 cursor-pointer place-items-center rounded-full border-0 bg-[#f4f3f1] active:scale-[0.98] active:brightness-[0.98]"
                >
                  <X className="h-2.5 w-2.5 text-black" strokeWidth={2.5} />
                </button>
              )}
            </header>
          )}

          {/* Scrollable body */}
          <div
            className={cn(
              'overflow-auto [-webkit-overflow-scrolling:touch]',
              (isFilter || isFullscreen) && 'z-[14] flex-1 overflow-y-auto',
            )}
            style={{ maxHeight: bodyMaxHeight }}
          >
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div className="px-2.5 pt-3.5 pb-[calc(18px+max(var(--ios-safe-bottom,0px),var(--tg-safe-area-bottom,0px)))]">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(sheet, document.body);
}
