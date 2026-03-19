"use client";

import styles from "./InfoCard.module.css";

export default function InfoCard({ title, iconSrc, index }) {
  return (
    <div className={`${styles.card} ${styles[`card${index}`]}`}>
      <p className={styles.title}>{title}</p>
      {iconSrc ? (
        <div className={styles.iconRow}>
          <img src={iconSrc} alt="" className={styles.icon} />
        </div>
      ) : null}
    </div>
  );
}
