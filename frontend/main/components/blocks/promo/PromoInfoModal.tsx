"use client";

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import styles from "./PromoInfoModal.module.css";

interface PromoInfoModalProps {
  open: boolean;
  onClose?: () => void;
}

/**
 * Нижнее модальное окно с описанием баллов (по макету Figma node 0-12811).
 */
export default function PromoInfoModal({ open, onClose }: PromoInfoModalProps) {
  const [visible, setVisible] = useState(open);
  const titleId = useId();
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) {
      const frame = requestAnimationFrame(() => setVisible(true));
      return () => cancelAnimationFrame(frame);
    }
    const timer = setTimeout(() => setVisible(false), 250);
    return () => clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };

    window.addEventListener("keydown", onKeyDown);
    closeBtnRef.current?.focus?.();

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  if (!visible) return null;

  return createPortal(
    <div
      className={styles.root}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div
        className={`${styles.backdrop} ${open ? styles.backdropOpen : styles.backdropClosed}`}
        onClick={onClose}
      />

      <div
        className={`${styles.sheetWrap} ${open ? styles.sheetOpen : styles.sheetClosed}`}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        <div className={styles.sheet}>
          <div className={styles.grabber} aria-hidden="true" />

          <header className={styles.header}>
            <h2 id={titleId} className={styles.title}>
              Баллы
            </h2>

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

          <div className={styles.body}>
            <section className={styles.block}>
              <h3 className={styles.blockTitle}>Как получить?</h3>
              <p className={styles.text}>
                За каждый завершённый заказ начисляется 200 баллов.
              </p>
            </section>

            <section className={styles.block}>
              <h3 className={styles.blockTitle}>Как потратить?</h3>
              <p className={styles.text}>
                Баллами можно оплачивать часть заказа: до 10% на стартовом
                уровне, до 15% на продвинутом и до 20% на премиум.
              </p>
            </section>

            <h3 className={styles.subTitle}>Подарочные баллы</h3>

            <section className={styles.block}>
              <h3 className={styles.blockTitle}>Как получить?</h3>
              <p className={styles.text}>
                Подарочные баллы начисляются при активации подарочной карты,
                полученной от другого пользователя.
              </p>
            </section>

            <section className={styles.block}>
              <h3 className={styles.blockTitle}>Как потратить?</h3>
              <p className={styles.text}>
                Подарочными баллами можно оплачивать до 100% стоимости заказа.
                При их наличии они всегда списываются первыми, пока не
                израсходуются полностью.
              </p>
            </section>
          </div>

          <div className={styles.footer}>
            <button type="button" onClick={onClose} className={styles.okButton}>
              Понятно
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
