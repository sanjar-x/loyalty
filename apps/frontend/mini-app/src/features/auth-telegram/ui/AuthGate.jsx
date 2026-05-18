'use client';

import { useAuthStore } from '@/features/auth-telegram';
import { AuthStatus } from '@/features/auth-telegram';

import styles from './AuthGate.module.css';

/**
 * AuthGate — renders children only in the `AUTHENTICATED` state.
 *
 * Goal: by the time RTK Query hooks mount, the `lm_access_token` cookie must
 * already be set. Otherwise every fetch receives `401 MISSING_TOKEN` and
 * triggers a 401→refresh→expired→re-auth loop.
 *
 * Bootstrap (`TelegramAuthBootstrap`) must be placed OUTSIDE this gate —
 * otherwise it would never run.
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
    // Case when opened in a phone browser (no Telegram SDK) — we redirect the user
    // to the Mini App; for a network error, retry via "Retry".
    const isMissingTelegram = error === 'OPEN_IN_TELEGRAM';

    return (
      <div className={styles.root} role="alert" aria-live="assertive">
        <div className={styles.card}>
          <div className={styles.title}>
            {isMissingTelegram ? 'Откройте через Telegram' : 'Не удалось войти'}
          </div>
          <div className={styles.subtitle}>
            {isMissingTelegram
              ? 'Это приложение работает только в мини-приложении Telegram.'
              : 'Проверьте подключение и попробуйте ещё раз.'}
          </div>
          {!isMissingTelegram ? (
            <button type="button" className={styles.retry} onClick={() => sessionExpired()}>
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
