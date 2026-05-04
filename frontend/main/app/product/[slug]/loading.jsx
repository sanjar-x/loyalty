import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Layout";
import styles from "./page.module.css";
import cx from "clsx";

export default function ProductLoading() {
  return (
    <main
      className={cx("tg-viewport", styles.c1, styles.tw1)}
      aria-busy="true"
    >
      <Container>
        <section className={styles.hero}>
          <div className={styles.skeleton}>
            <div className={cx(styles.skBlock, styles.skImage)} />
          </div>

          <div className={styles.skChips} aria-hidden="true">
            <div className={cx(styles.skBlock, styles.skChip, styles.skChip1)} />
            <div className={cx(styles.skBlock, styles.skChip, styles.skChip2)} />
            <div className={cx(styles.skBlock, styles.skChip, styles.skChip3)} />
          </div>

          <div className={styles.skInfo} aria-hidden="true">
            <div className={cx(styles.skBlock, styles.skLine, styles.skLine1)} />
            <div className={cx(styles.skBlock, styles.skLine, styles.skLine2)} />
            <div className={styles.skThumbs}>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className={cx(styles.skBlock, styles.skThumb)} />
              ))}
            </div>
          </div>

          <div className={styles.skSizes} aria-hidden="true">
            <div className={cx(styles.skBlock, styles.skLine, styles.skLine1)} />
            <div className={styles.skSizesRow}>
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className={cx(styles.skBlock, styles.skSize)} />
              ))}
            </div>
          </div>
        </section>

        <section className={styles.skPrice} aria-hidden="true">
          <div className={styles.skPriceRow}>
            <div className={cx(styles.skBlock, styles.skPriceBig)} />
            <div className={cx(styles.skBlock, styles.skPriceSub)} />
          </div>
        </section>
      </Container>
      <Footer />
    </main>
  );
}
