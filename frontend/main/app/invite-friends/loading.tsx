"use client";

import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Layout";
import Header from "@/components/layout/Header";
import { cn } from "@/lib/format/cn";

import styles from "./page.module.css";

export default function Loading() {
  return (
    <main className={cn("tg-viewport", styles.page)} aria-busy="true">
      <Container className={styles.container}>
        <Header title="Зовите друзей" />

        <section className={styles.hero} aria-label="Invite friends">
          <div className={styles.skeletonIllustration} aria-hidden="true" />

          <div className={styles.skeletonTitleWrap} aria-hidden="true">
            <div className={styles.skeletonTitleLine} />
            <div className={styles.skeletonTitleLineShort} />
          </div>

          <div className={styles.skeletonSubtitleWrap} aria-hidden="true">
            <div className={styles.skeletonSubtitleLine} />
            <div className={styles.skeletonSubtitleLine} />
          </div>
        </section>

        <section
          className={styles.promoCard}
          aria-label="Промокод"
          aria-hidden="true"
        >
          <div className={styles.promoHeader}>
            <div className={styles.skeletonPromoPercent} />
            <div className={styles.skeletonPromoUntil} />
          </div>
          <div className={styles.skeletonPromoDesc} />
          <div className={styles.skeletonPromoDescShort} />
          <div className={styles.skeletonPromoButton} />
        </section>

        <section
          className={styles.section}
          aria-label="Ваша ссылка для приглашений"
          aria-hidden="true"
        >
          <div className={styles.skeletonSectionTitle} />
          <div className={styles.skeletonInput} />
          <div className={styles.skeletonShareButton} />
        </section>

        <section
          className={styles.statsCard}
          aria-label="Статистика"
          aria-hidden="true"
        >
          {Array.from({ length: 3 }).map((_, idx) => (
            <div key={idx}>
              <div className={styles.statRow}>
                <div className={styles.skeletonStatLabel} />
                <div className={styles.skeletonStatValue} />
              </div>
              {idx < 2 ? <div className={styles.divider} /> : null}
            </div>
          ))}
        </section>

        <section
          className={styles.history}
          aria-label="История приглашений"
          aria-hidden="true"
        >
          <div className={styles.historyTitle}>История приглашений</div>

          <ul className={styles.historyList}>
            {Array.from({ length: 3 }).map((_, idx) => (
              <li
                key={idx}
                className={styles.historyItem}
                style={
                  idx > 0
                    ? { borderTop: "1px solid rgba(0, 0, 0, 0.06)" }
                    : undefined
                }
              >
                <div className={styles.skeletonAvatar} />
                <div className={styles.skeletonHistoryBody}>
                  <div>
                    <div className={styles.skeletonHistoryName} />
                    <div className={styles.skeletonHistoryDate} />
                  </div>
                  <div className={styles.skeletonHistoryStatus} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      </Container>

      <Footer />
    </main>
  );
}
