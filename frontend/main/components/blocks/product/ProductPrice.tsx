"use client";
import React, { useState } from "react";
import Image from "next/image";
import styles from "./ProductPrice.module.css";
import SplitPaymentSheet from "./SplitPaymentSheet";

interface SplitPaymentData {
  amount?: string | number;
  count?: number;
  text?: string;
}

interface ProductPriceProps {
  price?: string;
  splitPayment?: SplitPaymentData;
  deliveryInfo?: string;
}

export default function ProductPrice({ price, splitPayment, deliveryInfo }: ProductPriceProps) {
  const [isSplitOpen, setIsSplitOpen] = useState<boolean>(false);

  const splitAmount = splitPayment?.amount ?? "";
  const splitAmountText = String(splitAmount).includes("\u20bd")
    ? String(splitAmount)
    : `${splitAmount}\u20bd`;

  return (
    <div className={styles.c1}>
      <div className={styles.c2}>
        {/* Цена */}
        <div className={styles.c3}>
          <h2 className={styles.c4}>{price}</h2>
          {deliveryInfo && (
            <div className={styles.c5}>
              <p className={styles.c6}>{deliveryInfo}</p>
              <span className={styles.infoIcon} aria-hidden="true">
                i
              </span>
            </div>
          )}
        </div>

        {/* Рассрочка / Оплата частями */}
        {splitPayment && (
          <div className={styles.splitRow}>
            <div className={styles.splitLeft}>
              <span className={styles.splitIcon} aria-hidden="true">
                <Image src="/icons/global/split.svg" alt="" fill sizes="34px" />
              </span>
              <div className={styles.splitText}>
                <div className={styles.splitTop}>
                  <span className={styles.splitTopText}>
                    {splitPayment.count} \u00d7 {splitAmountText}{" "}
                    <span>\u0432 \u0441\u043f\u043b\u0438\u0442</span>
                  </span>
                </div>
                <p className={styles.splitSub}>
                  {splitPayment.text || "\u0411\u0435\u0437 \u043f\u0435\u0440\u0435\u043f\u043b\u0430\u0442\u044b"}
                </p>
              </div>
            </div>

            <button
              type="button"
              className={styles.splitAction}
              aria-label="\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438"
              aria-haspopup="dialog"
              aria-expanded={isSplitOpen}
              onClick={() => setIsSplitOpen(true)}
            >
              <Image
                src="/icons/product/constructor-icon.svg"
                alt=""
                width={18}
                height={18}
              />
            </button>

            <SplitPaymentSheet
              open={isSplitOpen}
              onClose={() => setIsSplitOpen(false)}
              price={price}
              splitPayment={splitPayment}
            />
          </div>
        )}
      </div>
    </div>
  );
}
