'use client';

import Image from 'next/image';
import styles from './InfoCard.module.css';

export default function InfoCard({ title, iconSrc, index }) {
  return (
    <div className={`${styles.card} ${styles[`card${index}`]}`}>
      <p className={styles.title}>{title}</p>
      {iconSrc ? (
        <div className={styles.iconRow}>
          <Image src={iconSrc} alt="" className={styles.icon} width={79} height={79} />
        </div>
      ) : null}
    </div>
  );
}
