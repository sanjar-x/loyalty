import Link from 'next/link';
import Footer from '@/components/layout/Footer';
import Container from '@/components/layout/Container';
import styles from './page.module.css';
import cx from 'clsx';

export const metadata = {
  title: 'Товар не найден — Loyalty Market',
  robots: { index: false, follow: false },
};

export default function ProductNotFound() {
  return (
    <main className={cx('tg-viewport', styles.c1, styles.tw1)}>
      <Container>
        <section className={styles.hero}>
          <div className={styles.aboutTitle}>Товар не найден</div>
          <p style={{ opacity: 0.7, margin: '8px 0 16px' }}>
            Возможно, товар снят с продажи или ссылка устарела.
          </p>
          <Link href="/catalog" className={styles.supportBtn}>
            В каталог
          </Link>
        </section>
      </Container>
      <Footer />
    </main>
  );
}
