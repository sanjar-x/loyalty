"use client";

import Image from "next/image";
import SearchBar from "@/components/blocks/search/SearchBar";
import Footer from "@/components/layout/Footer";

import styles from "./page.module.css";

export default function Loading(): React.JSX.Element {
  return (
    <div className={styles.root}>
      <h3 className={styles.searchTitle}>Каталог</h3>
      <SearchBar />

      <main className={styles.main}>
        <div className={styles.sectionHeader} aria-hidden="true">
          <div className={styles.headerRow}>
            <div className={styles.skeletonTitle} />
            <button type="button" className={styles.allBtn}>
              <span className={styles.allText}>все</span>
              <div className={styles.allIconWrap}>
                <Image
                  src="/icons/global/Wrap.svg"
                  alt=""
                  width={16}
                  height={15}
                />
              </div>
            </button>
          </div>
        </div>

        <div className={styles.listOuter} aria-busy="true">
          <div className={styles.list}>
            <div className={`${styles.divider} ${styles.dividerTop}`} />

            <div className={styles.items}>
              {Array.from({ length: 10 }).map((_, idx) => (
                <div key={idx}>
                  <div className={styles.itemRow}>
                    <div className={styles.skeletonType} />
                    <div className={styles.chevron}>
                      <div className={styles.skeletonChevron} />
                    </div>
                  </div>
                  {idx < 9 ? <div className={styles.divider} /> : null}
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
