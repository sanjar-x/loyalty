"use client";
import React from "react";
import styles from "./EmptyState.module.css";
import cx from "clsx";

export default function EmptyState() {
  return (
    <div className={styles.c1}>
      <div className={cx(styles.c2, styles.tw1)}>
        <img
          className={styles.heart}
          src="/img/fauriteHeadrtImg.png"
          alt=""
          aria-hidden="true"
        />
        <h2 className={styles.c3}>В избранном пока пусто</h2>
        <p className={styles.c4}>
          Добавляйте товары в избранное, чтобы купить их позже
        </p>
      </div>
    </div>
  );
}
