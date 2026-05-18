'use client';

import Footer from '@/widgets/Footer';
import Header from '@/widgets/Header';

import styles from './page.module.css';

function openInTelegram(url) {
  const tg = typeof window !== 'undefined' && window.Telegram?.WebApp;
  if (tg?.openLink) {
    tg.openLink(url, { try_instant_view: true });
  } else {
    window.open(url, '_blank', 'noopener');
  }
}

export default function AboutPage() {
  return (
    <div className={styles.page}>
      <Header title="О сервисе" />
      <main className={styles.main}>
        <section className={styles.brand} aria-label="О сервисе">
          <div className={styles.logo} aria-hidden="true">
            <img src="/icons/global/aboutUs.svg" alt="aboutUSIcon" />
          </div>
          <div className={styles.copy}>© 2026 «loyalty market»</div>
        </section>

        <section className={styles.cardWrapper} aria-label="Документы">
          <div className={styles.card}>
            <button
              type="button"
              className={styles.row}
              onClick={() => openInTelegram('https://teletype.in/@loyaltymarket/user-agreement')}
            >
              <div className={styles.rowText}>Пользовательское соглашение</div>
              <img
                src="/icons/global/small-arrow.svg"
                alt=""
                aria-hidden="true"
                className={styles.rowArrow}
              />
            </button>

            <div className={styles.divider} aria-hidden="true" />

            <button
              type="button"
              className={styles.row}
              onClick={() => openInTelegram('https://teletype.in/@loyaltymarket/public-offer')}
            >
              <div className={styles.rowText}>Публичная оферта</div>
              <img
                src="/icons/global/small-arrow.svg"
                alt=""
                aria-hidden="true"
                className={styles.rowArrow}
              />
            </button>

            <div className={styles.divider} aria-hidden="true" />

            <button
              type="button"
              className={styles.row}
              onClick={() => openInTelegram('https://teletype.in/@loyaltymarket/privacy-policy')}
            >
              <div className={styles.rowText}>Политика конфиденциальности</div>
              <img
                src="/icons/global/small-arrow.svg"
                alt=""
                aria-hidden="true"
                className={styles.rowArrow}
              />
            </button>

            <div className={styles.divider} aria-hidden="true" />

            <button
              type="button"
              className={styles.row}
              onClick={() =>
                openInTelegram(
                  'https://teletype.in/@loyaltymarket/consent-to-personal-data-processing'
                )
              }
            >
              <div className={styles.rowTextFade}>Согласие на обработку персональных данных</div>
              <img
                src="/icons/global/small-arrow.svg"
                alt=""
                aria-hidden="true"
                className={styles.rowArrow}
              />
            </button>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
