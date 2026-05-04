"use client";

import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Layout";
import styles from "./page.module.css";
import cx from "clsx";

export default function ProductError({ reset }) {
  return (
    <main className={cx("tg-viewport", styles.c1, styles.tw1)}>
      <Container>
        <section className={styles.hero}>
          <div className={styles.aboutTitle}>Ошибка загрузки товара</div>
          <p style={{ opacity: 0.7, margin: "8px 0 16px" }}>
            Попробуйте обновить страницу или вернуться позже.
          </p>
          <button
            type="button"
            className={styles.supportBtn}
            onClick={() => reset?.()}
          >
            Повторить
          </button>
        </section>
      </Container>
      <Footer />
    </main>
  );
}
