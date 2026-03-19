"use client";

import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import styles from "./comingSoon.module.css";

export default function ComingSoon({
  title,
  subtitle = "Скоро здесь появится функционал.",
}) {
  return (
    <>
      <main className={styles.page}>
        <section className={styles.center} aria-label="Страница в разработке">
          <h2 className={styles.title}>Страница в разработке</h2>
          <p className={styles.subtitle}>{subtitle}</p>
        </section>
      </main>
      <Footer />
    </>
  );
}
