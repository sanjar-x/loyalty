"use client";

import React, { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

import styles from "./BottomSheet.module.css";

const ANIMATION_MS = 240;
const UNMOUNT_DELAY_MS = ANIMATION_MS + 30;

interface BottomSheetProps {
  isTypeModule?: boolean;
  isFilter?: boolean;
  open: boolean;
  onClose: () => void;
  title?: string;
  ariaLabel?: string;
  header?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  maxHeightOffset?: number;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  isReview?: boolean;
  isPromocodePage?: boolean;
}

export default function BottomSheet({
  isTypeModule,
  isFilter,
  open,
  onClose,
  title,
  ariaLabel,
  header,
  children,
  footer,
  maxHeightOffset = 24,
  initialFocusRef,
  isReview,
  isPromocodePage,
}: BottomSheetProps) {
  const [mounted, setMounted] = useState(open);
  const [active, setActive] = useState(false);
  const titleId = useId();
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    let frame1 = 0;
    let frame2 = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    if (open) {
      // Mount first (closed), then flip to active next frame so CSS transition runs.
      frame1 = requestAnimationFrame(() => {
        setMounted(true);
        setActive(false);
        frame2 = requestAnimationFrame(() => setActive(true));
      });
    } else {
      // Start exit animation, then unmount after transition.
      frame1 = requestAnimationFrame(() => setActive(false));
      timer = setTimeout(() => setMounted(false), UNMOUNT_DELAY_MS);
    }

    return () => {
      if (frame1) cancelAnimationFrame(frame1);
      if (frame2) cancelAnimationFrame(frame2);
      if (timer) clearTimeout(timer);
    };
  }, [open]);

  useEffect(() => {
    if (!mounted) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current?.();
    };

    window.addEventListener("keydown", onKeyDown);
    if (open) {
      const el = initialFocusRef?.current || closeBtnRef.current;
      // Avoid stealing focus from active elements during re-renders.
      if (el && document.activeElement !== el) el?.focus?.();
    }

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [initialFocusRef, mounted, open]);

  if (!mounted) return null;

  const sheet = (
    <div
      className={styles.root}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title && !ariaLabel ? titleId : undefined}
      aria-label={!title && ariaLabel ? ariaLabel : undefined}
    >
      <div
        className={`${styles.backdrop} ${active ? styles.backdropOpen : styles.backdropClosed}`}
        onClick={onClose}
      />

      <div
        className={`${styles.sheetWrap} ${active ? styles.sheetOpen : styles.sheetClosed}`}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
        style={{ minHeight: `${isTypeModule ? `80vh` : "auto"}` }}
      >
        <div
          className={`${styles.sheet} ${isReview ? `${styles.isReview}` : ""} ${isTypeModule ? `${styles.isTypeModule}` : ""} ${isFilter ? `${styles.isFilter}` : ""}`}
          style={{
            maxHeight: `min(85vh, calc(var(--tg-viewport-stable-height, 100vh) - ${maxHeightOffset}px))`,
            height: `${isReview ? "auto" : "min(85vh)"}, calc(var(--tg-viewport-stable-height, 100vh) - ${maxHeightOffset}px))`,
          }}
        >
          <div className={styles.grabber} aria-hidden="true" />

          {header ? (
            header
          ) : (
            <header className={styles.header}>
              {title ? (
                <h2 id={titleId} className={styles.title}>
                  {title}
                </h2>
              ) : (
                <div />
              )}

              <button
                ref={closeBtnRef}
                type="button"
                aria-label="Закрыть"
                onClick={onClose}
                className={styles.closeBtn}
              >
                <span className={styles.closeIcon} aria-hidden="true">
                  <img src="/icons/global/markXBlack.svg" alt="markX" />
                </span>
              </button>
            </header>
          )}

          <div
            className={`${styles.body} ${isPromocodePage ? `${styles.isPromocodePage}` : ""} ${isReview ? `${styles.isReview}` : ""} ${isTypeModule ? `${styles.isTypeModule}` : ""}`}
            style={{
              maxHeight: `${isReview ? "auto" : "446px"}`,
            }}
          >
            {children}
          </div>

          {footer ? <div className={styles.footer}>{footer}</div> : null}
        </div>
      </div>
    </div>
  );

  return createPortal(sheet, document.body);
}
