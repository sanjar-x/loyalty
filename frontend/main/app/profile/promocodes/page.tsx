"use client";

import { useCallback, useMemo, useState } from "react";

import Footer from "@/components/layout/Footer";
import Header from "@/components/layout/Header";
import BottomSheet from "@/components/ui/BottomSheet";

import styles from "./page.module.css";

interface PromoCode {
  id: string;
  code: string;
  subtitle: string;
  until: string;
}

export default function PromoCodesPage() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [activePromo, setActivePromo] = useState<PromoCode | null>(null);
  const [copied, setCopied] = useState(false);

  const promoCodes = useMemo<PromoCode[]>(
    () => [
      {
        id: "pc-1",
        code: "GNRA45KH",
        subtitle: "-5% на товары из категории товаров одежды",
        until: "до 29.11.25",
      },
      {
        id: "pc-2",
        code: "Kkkkkkkkkkkkkkkkkkkkkkkkk",
        subtitle: "Kkkkkkkkkkkkkkkkkkkkkkkkk...",
        until: "до 31.09.2025",
      },
    ],
    [],
  );

  const closeSheet = useCallback(() => {
    setSheetOpen(false);
    setActivePromo(null);
    setCopied(false);
  }, []);

  const copyText = useCallback(async (text: string): Promise<boolean> => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(String(text));
        return true;
      }
    } catch {
      // fallback below
    }

    try {
      const value = String(text);
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.top = "0";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);

      textarea.focus();
      textarea.select();
      try {
        textarea.setSelectionRange(0, value.length);
      } catch {
        // ignore
      }

      const ok = document.execCommand?.("copy") ?? false;
      document.body.removeChild(textarea);
      return Boolean(ok);
    } catch {
      return false;
    }
  }, []);

  const doCopy = useCallback(async () => {
    if (!activePromo?.code) return;
    const ok = await copyText(activePromo.code);

    if (ok) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
      return;
    }

    const tg = (window as Record<string, unknown>).Telegram as Record<string, unknown> | undefined;
    const webApp = tg?.WebApp as Record<string, unknown> | undefined;
    if (webApp?.showPopup) {
      try {
        (webApp.showPopup as (opts: { message: string }) => void)({
          message:
            "Не удалось скопировать промокод. Попробуйте выделить и скопировать вручную.",
        });
      } catch {
        // ignore
      }
    }
  }, [activePromo, copyText]);

  return (
    <div className={styles.page}>
      <Header title="Промокоды" />

      <main className={styles.main}>
        {promoCodes.length ? (
          <div className={styles.list}>
            {promoCodes.map((item) => (
              <button
                key={item.id}
                type="button"
                className={styles.row}
                onClick={() => {
                  setActivePromo(item);
                  setSheetOpen(true);
                }}
              >
                <div className={styles.rowIcon} aria-hidden="true" />

                <div className={styles.rowText}>
                  <div className={styles.rowTitle}>{item.code}</div>
                  <div className={styles.rowSubtitle}>{item.subtitle}</div>
                </div>

                <img
                  src="/icons/global/small-arrow.svg"
                  alt=""
                  aria-hidden="true"
                  className={styles.rowArrow}
                />
              </button>
            ))}
          </div>
        ) : (
          <div className={styles.empty} role="status" aria-live="polite">
            <div className={styles.emptyTitle}>Промокодов пока нет</div>
            <div className={styles.emptySubtitle}>
              Они будут появляться здесь,
              <br />
              как только вы их получите
            </div>
          </div>
        )}
      </main>

      <BottomSheet
        open={sheetOpen}
        onClose={closeSheet}
        ariaLabel="Промокод"
        header={<div className={styles.sheetHeader} />}
        isPromocodePage={true}
      >
        <div className={styles.sheetContent}>
          <div className={styles.sheetTop}>
            <div className={styles.sheetTitle}>
              Промокод {activePromo?.code}
            </div>
            <button
              type="button"
              className={styles.sheetCloseBtn}
              aria-label="Закрыть"
              onClick={closeSheet}
            >
              <span className={styles.sheetCloseIcon} aria-hidden="true">
                <img src="/icons/global/markXBlack.svg" alt="markX" />
              </span>
            </button>
          </div>

          <div className={styles.sheetDescription}>{activePromo?.subtitle}</div>
          <div className={styles.sheetUntil}>{activePromo?.until}</div>

          <button type="button" className={styles.copyBtn} onClick={doCopy}>
            {copied ? "Скопировано" : "Скопировать"}
          </button>
        </div>
      </BottomSheet>

      <Footer />
    </div>
  );
}
