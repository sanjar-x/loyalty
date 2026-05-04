"use client";

import { useAuthStore } from "@/lib/features/auth/store";
import { AuthStatus } from "@/lib/features/auth/types";

import styles from "./auth-gate.module.css";

/**
 * AuthGate — children'ni faqat `AUTHENTICATED` holatida render qiladi.
 *
 * Maqsad: RTK Query hook'lari mount bo'lgunga qadar `lm_access_token` cookie
 * o'rnatilgan bo'lsin. Aks holda har bir fetch `401 MISSING_TOKEN` oladi va
 * 401→refresh→expired→re-auth loop'ini qo'zg'atadi.
 *
 * Bootstrap (`TelegramAuthBootstrap`) shu gate'dan TASHQARIDA joylashishi
 * shart — aks holda hech qachon ishga tushmaydi.
 */
export default function AuthGate({ children }) {
  const status = useAuthStore((s) => s.status);
  const isVerifying = useAuthStore((s) => s.isVerifying);
  const error = useAuthStore((s) => s.error);
  const sessionExpired = useAuthStore((s) => s.sessionExpired);

  if (status === AuthStatus.AUTHENTICATED && !isVerifying) {
    return children;
  }

  if (status === AuthStatus.ERROR) {
    // Telefon brauzerida (Telegram SDK yo'q) ochilgan holat — foydalanuvchini
    // Mini App'ga yo'naltiramiz; tarmoq xatosi bo'lsa "Повторить" bilan retry.
    const isMissingTelegram = error === "OPEN_IN_TELEGRAM";

    return (
      <div className={styles.root} role="alert" aria-live="assertive">
        <div className={styles.card}>
          <div className={styles.title}>
            {isMissingTelegram
              ? "Откройте через Telegram"
              : "Не удалось войти"}
          </div>
          <div className={styles.subtitle}>
            {isMissingTelegram
              ? "Это приложение работает только в мини-приложении Telegram."
              : "Проверьте подключение и попробуйте ещё раз."}
          </div>
          {!isMissingTelegram ? (
            <button
              type="button"
              className={styles.retry}
              onClick={() => sessionExpired()}
            >
              Повторить
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  // IDLE | LOADING | EXPIRED | LOGGED_OUT — splash
  return (
    <div className={styles.root} aria-busy="true" aria-live="polite">
      <div className={styles.spinner} aria-hidden="true" />
    </div>
  );
}
