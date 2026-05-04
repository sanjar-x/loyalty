"use client";

import Image from "next/image";
import styles from "./ProductShippingOptions.module.css";

export default function ProductShippingOptions({
  pickupTitle = "Самовывоз",
  pickupDate = "Сегодня",
  pickupSub = "из наличия",
  pickupAddress = "Оренбург, улица Пролетарская, 23, 2 этаж",
  deliveryTitle = "Доставка",
  deliveryDate = "Послезавтра",
  deliverySub = "из наличия",
  deliveryHint = "В пункт выдачи от 99₽",
}) {
  const pickupCity = String(pickupAddress || "")
    .split(",")[0]
    ?.trim();

  return (
    <section className={styles.root}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h3 className={styles.title}>{pickupTitle}</h3>
        </div>

        <div className={styles.row}>
          <span className={styles.dot} aria-hidden="true" />
          <div className={styles.pickupAddress}>
            <div className={styles.text}>
              <p className={styles.line1}>
                <span className={styles.strong}>{pickupDate}</span>
                <span className={styles.muted}>, {pickupSub}</span>
                {pickupCity ? (
                  <>
                    <span className={styles.sep} aria-hidden="true">
                      •
                    </span>
                    <span className={styles.muted}>{pickupCity}</span>
                  </>
                ) : null}
              </p>
              <p className={styles.line2}>{pickupAddress}</p>
            </div>
            <button
              type="button"
              className={styles.iconBtn}
              aria-label="Навигация"
            >
              <Image
                src="/icons/product/cursor.svg"
                alt=""
                width={18}
                height={18}
              />
            </button>
          </div>
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles.header}>
          <h3 className={styles.title}>{deliveryTitle}</h3>
        </div>

        <div className={styles.row}>
          <span className={styles.dot} aria-hidden="true" />
          <div className={styles.text}>
            <p className={styles.line1}>
              <span className={styles.strong}>{deliveryDate}</span>,{" "}
              <span className={styles.muted}>{deliverySub}</span>
            </p>
            <p className={styles.line2}>{deliveryHint}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
