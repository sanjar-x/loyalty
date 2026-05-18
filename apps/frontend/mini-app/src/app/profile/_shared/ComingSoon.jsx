'use client';

import Header from '@/widgets/Header';
import Footer from '@/widgets/Footer';
import styles from './ComingSoon.module.css';

export default function ComingSoon({ title, subtitle = 'Скоро здесь появится функционал.' }) {
  return (
    <>
      <Header title={title} />
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
