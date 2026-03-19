"use client";
import React from "react";
import Link from "next/link";
import styles from "./ProfileHeader.module.css";
import cx from "clsx";

export default function ProfileHeader({ name, avatar }) {
  return (
    <div className={styles.c1}>
      {/* Аватар */}
      <div className={cx(styles.c2, styles.tw1)}>
        <div className={styles.c3}>
          {avatar ? (
            <img src={avatar} alt={name} className={styles.c4} />
          ) : (
            <div className={styles.c5} />
          )}
        </div>
      </div>

      {/* Имя и кнопка настроек */}
      <div className={cx(styles.c6, styles.tw2)}>
        <h2 className={styles.c7}>{name}</h2>
        <Link href="/profile/settings" className={cx(styles.c8, styles.tw3)}>
          <span>Настройки</span>
          <img
            src="/icons/global/Wrap.svg"
            alt="arrow"
            className={cx(styles.c9, styles.tw4)}
          />
        </Link>
      </div>
    </div>
  );
}
