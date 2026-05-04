"use client";
import React from "react";
import Image from "next/image";
import styles from "./EmptyState.module.css";
import cx from "clsx";

export default function EmptyState() {
  return (
    <div className={styles.c1}>
      <div className={cx(styles.c2, styles.tw1)}>
        <Image
          className={styles.heart}
          src="/img/fauriteHeadrtImg.webp"
          alt=""
          aria-hidden="true"
          width={100}
          height={100}
        />
        <h2 className={styles.c3}>В избранном пока пусто</h2>
        <p className={styles.c4}>
          Добавляйте товары в избранное, чтобы купить их позже
        </p>
      </div>
    </div>
  );
}
