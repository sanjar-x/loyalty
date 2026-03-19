"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { Check } from "lucide-react";

import styles from "./page.module.css";

export default function InviteLinkActions({ url }) {
  const [copied, setCopied] = useState(false);
  const [hint, setHint] = useState("");
  const inputRef = useRef(null);

  const shareText = useMemo(() => `Присоединяйся к LOYALTY: ${url}`, [url]);

  const copyText = useCallback(async (text) => {
    // Modern clipboard API (may be blocked in Telegram/iOS).
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      // fallback below
    }

    // Fallback for iOS/Telegram: execCommand('copy') with a temporary textarea.
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
    const ok = await copyText(url);

    if (ok) {
      setCopied(true);
      setHint("Ссылка скопирована");
      window.setTimeout(() => {
        setCopied(false);
        setHint("");
      }, 1200);
      return;
    }

    // If copy failed, focus/select the input so user can long-press to copy.
    setHint("Не удалось скопировать — зажмите ссылку и скопируйте вручную");
    inputRef.current?.focus?.();
    inputRef.current?.select?.();

    const tg = window.Telegram?.WebApp;
    if (tg?.showPopup) {
      try {
        tg.showPopup({
          message:
            "Не удалось скопировать. Зажмите ссылку и скопируйте вручную.",
        });
      } catch {
        // ignore
      }
    }
  }, [copyText, url]);

  const onShare = useCallback(async () => {
    // Prefer native share where available; fallback to copy.
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({ text: shareText, url });
        return;
      }
    } catch {
      // ignore
    }

    // Telegram WebApp may provide its own APIs; we still keep this safe in browsers.
    const tg = window.Telegram?.WebApp;
    if (tg?.openTelegramLink) {
      try {
        const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(shareText)}`;
        tg.openTelegramLink(shareUrl);
        return;
      } catch {
        // ignore
      }
    }

    // Last fallback: copy link.
    await doCopy();
  }, [doCopy, shareText, url]);

  return (
    <div className={styles.actions}>
      <div className={styles.linkRow}>
        <input
          type="text"
          aria-label="Ссылка для приглашения"
          value={url}
          readOnly
          className={styles.linkInput}
          ref={inputRef}
          onClick={(e) => e.currentTarget.select()}
        />

        <button
          type="button"
          className={`${styles.copyButton} ${copied ? styles.copyButtonCopied : ""}`}
          aria-label={copied ? "Скопировано" : "Скопировать ссылку"}
          onClick={doCopy}
        >
          {copied ? (
            <Check className={styles.copyIcon} aria-hidden="true" />
          ) : (
            <img
              src="/icons/invite-friends/copy.svg"
              alt=""
              className={styles.copyIcon}
            />
          )}
        </button>
      </div>

      <button
        type="button"
        className={styles.shareButton}
        aria-label="Поделиться ссылкой"
        onClick={onShare}
      >
        Поделиться
      </button>

      <div className={styles.hint} aria-live="polite">
        {hint}
      </div>
    </div>
  );
}
