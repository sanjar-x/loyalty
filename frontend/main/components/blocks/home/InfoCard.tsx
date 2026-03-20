"use client";

import styles from "./InfoCard.module.css";

interface InfoCardProps {
  title: string;
  iconSrc?: string;
  index: number;
}

export default function InfoCard({ title, iconSrc, index }: InfoCardProps) {
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
