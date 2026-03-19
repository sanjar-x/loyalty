"use client";

import Footer from "@/components/layout/Footer";

import styles from "./page.module.css";

export default function AboutPage() {
  return (
    <div className={styles.page}>
      <h3 className={styles.aboutTitle}>О сервисе</h3>
      <main className={styles.main}>
        <section className={styles.brand} aria-label="О сервисе">
          <div className={styles.logo} aria-hidden="true">
            <img src="/icons/global/aboutUs.png" alt="aboutUSIcon" />
          </div>
          <div className={styles.copy}>© 2025 «loyalty market»</div>
        </section>

        <section className={styles.cardWrapper} aria-label="Документы">
          <div className={styles.card}>
            <button
              type="button"
              className={styles.row}
              onClick={() => {
                // TODO: open user agreement
              }}
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
              onClick={() => {
                // TODO: open public offer
              }}
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
              onClick={() => {
                // TODO: open privacy policy
              }}
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
              onClick={() => {
                // TODO: open personal data processing consent
              }}
            >
              <div className={styles.rowText}>
                Согласие на обработку персональных данных
              </div>
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
