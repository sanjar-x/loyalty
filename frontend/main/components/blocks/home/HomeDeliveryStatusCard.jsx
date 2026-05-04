"use client";

import styles from "./HomeDeliveryStatusCard.module.css";

export default function HomeDeliveryStatusCard() {
  return (
    <div className={styles.outer}>
      <div className={styles.card}>
        <div className={styles.iconWrap}>
          <img
            src="/icons/global/shipping.svg"
            alt="delivery"
            className={styles.icon}
          />
        </div>
        <div className={styles.text}>
          <div className={styles.title}>Отправлен в пункт выдачи</div>
          <div className={styles.subtitle}>Примерный срок доставки 6 мая</div>
        </div>
      </div>
    </div>
  );
}
