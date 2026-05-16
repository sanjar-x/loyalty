import Link from 'next/link';
import Footer from '@/components/layout/Footer';
import Header from '@/components/layout/Header';
import styles from './page.module.css';

export default function CategoryNotFound() {
  return (
    <div className={styles.root}>
      <Header title="Каталог" />
      <main className={styles.main}>
        <div className={styles.sectionHeader}>
          <h1 className={styles.title}>Категория не найдена</h1>
          <p style={{ color: '#7e7e7e', marginTop: 8, fontSize: 14 }}>
            Возможно, категория была удалена или переименована.
          </p>
          <Link
            href="/catalog"
            style={{
              display: 'inline-block',
              marginTop: 16,
              color: '#111',
              textDecoration: 'underline',
              fontSize: 14,
            }}
          >
            Вернуться в каталог
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
