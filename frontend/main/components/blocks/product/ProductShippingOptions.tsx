"use client";

import Image from "next/image";
import styles from "./ProductShippingOptions.module.css";

interface ProductShippingOptionsProps {
  pickupTitle?: string;
  pickupDate?: string;
  pickupSub?: string;
  pickupAddress?: string;
  deliveryTitle?: string;
  deliveryDate?: string;
  deliverySub?: string;
  deliveryHint?: string;
}

export default function ProductShippingOptions({
  pickupTitle = "\u0421\u0430\u043c\u043e\u0432\u044b\u0432\u043e\u0437",
  pickupDate = "\u0421\u0435\u0433\u043e\u0434\u043d\u044f",
  pickupSub = "\u0438\u0437 \u043d\u0430\u043b\u0438\u0447\u0438\u044f",
  pickupAddress = "\u041e\u0440\u0435\u043d\u0431\u0443\u0440\u0433, \u0443\u043b\u0438\u0446\u0430 \u041f\u0440\u043e\u043b\u0435\u0442\u0430\u0440\u0441\u043a\u0430\u044f, 23, 2 \u044d\u0442\u0430\u0436",
  deliveryTitle = "\u0414\u043e\u0441\u0442\u0430\u0432\u043a\u0430",
  deliveryDate = "\u041f\u043e\u0441\u043b\u0435\u0437\u0430\u0432\u0442\u0440\u0430",
  deliverySub = "\u0438\u0437 \u043d\u0430\u043b\u0438\u0447\u0438\u044f",
  deliveryHint = "\u0412 \u043f\u0443\u043d\u043a\u0442 \u0432\u044b\u0434\u0430\u0447\u0438 \u043e\u0442 99\u20bd",
}: ProductShippingOptionsProps) {
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
                      {"\u2022"}
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
              aria-label="\u041d\u0430\u0432\u0438\u0433\u0430\u0446\u0438\u044f"
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
