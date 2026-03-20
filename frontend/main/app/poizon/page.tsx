"use client";

import Footer from "@/components/layout/Footer";
import styles from "./page.module.css";

export default function PoizonPage() {
  return (
    <>
      <div className={styles.page}>
        <div className={styles.topbarTitle}>Poizon</div>

        <main className={styles.main}>
          <section className={styles.center} aria-label="Страница в разработке">
            <h2 className={styles.title}>Страница в разработке</h2>
            <p className={styles.subtitle}>
              Скоро здесь появится возомжность покупать оригинальные товары
            </p>
          </section>
        </main>
      </div>

      <Footer />
    </>
  );
}
