import styles from './PageStub.module.css';

export function PageStub({ title }) {
  return (
    <section className={styles.root}>
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.subtitle}>Раздел в разработке.</p>
    </section>
  );
}
