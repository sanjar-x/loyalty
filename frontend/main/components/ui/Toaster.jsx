"use client";

import { useToastStore } from "@/lib/ui/toast";

import styles from "./Toaster.module.css";

/**
 * Global toast renderer — bitta `<Toaster />` layout.tsx'da mount qilinadi.
 * Store'dan toast ro'yxatini o'qiydi va auto-dismiss timer'ini boshqaradi
 * (timer toast.js'da, bu yerda faqat render).
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
          role={t.type === "error" ? "alert" : "status"}
          className={`${styles.toast} ${
            t.type === "error"
              ? styles.toastError
              : t.type === "success"
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
