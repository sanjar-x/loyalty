'use client';

import { useToastStore } from '@/shared/ui/Toaster';

import styles from './Toaster.module.css';

/**
 * Global toast renderer — a single `<Toaster />` is mounted in layout.tsx.
 * It reads the toast list from the store and drives the auto-dismiss timer
 * (the timer lives in toast.js, only rendering is done here).
 */
export default function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  if (toasts.length === 0) return null;

  return (
    <div className={styles.root} aria-live="polite" aria-atomic="false">
      {toasts.map((t) => (
        <div
          key={t.id}
          role={t.type === 'error' ? 'alert' : 'status'}
          className={`${styles.toast} ${
            t.type === 'error'
              ? styles.toastError
              : t.type === 'success'
                ? styles.toastSuccess
                : styles.toastInfo
          }`}
          onClick={() => dismiss(t.id)}
        >
          <span className={styles.message}>{t.message}</span>
        </div>
      ))}
    </div>
  );
}
