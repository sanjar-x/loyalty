"use client";

import { useCallback, useState } from "react";

import styles from "./page.module.css";

export default function PromoCouponCard({
  percent,
  until,
  description,
  copyValue,
}) {
  const [copied, setCopied] = useState(false);

  const copyText = useCallback(async (text) => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      // fallback below
    }

    try {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.top = "0";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);

      textarea.focus();
      textarea.select();
      textarea.setSelectionRange(0, text.length);

      const ok = document.execCommand("copy");
      document.body.removeChild(textarea);
      return ok;
    } catch {
      return false;
    }
  }, []);

  const doCopy = useCallback(async () => {
    const ok = await copyText(copyValue);

    if (ok) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
      return;
    }

    const tg = window.Telegram?.WebApp;
    if (tg?.showPopup) {
      try {
        tg.showPopup({
          message:
            "Не удалось скопировать промокод. Попробуйте выделить и скопировать вручную.",
        });
      } catch {
        // ignore
      }
    }
  }, [copyText, copyValue]);

  return (
    <section className={styles.promoCard} aria-label="Промокод">
      <div className={styles.promoHeader}>
        <div className={styles.promoPercent}>{percent}%</div>
        <div className={styles.promoUntil}>{until}</div>
      </div>

      <p className={styles.promoDescription}>{description}</p>

      <button
        type="button"
        className={styles.promoCopyButton}
        onClick={doCopy}
        aria-label="Скопировать промокод"
      >
        {copied ? "Скопировано" : "Скопировать"}
      </button>
    </section>
  );
}
