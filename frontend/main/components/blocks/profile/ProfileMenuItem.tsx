"use client";
import React from "react";
import Link from "next/link";
import styles from "./ProfileMenuItem.module.css";
import cx from "clsx";

interface MenuItemProps {
  text: string;
  icon?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  fontWeight?: 400 | 500 | 600;
  badge?: string | number;
  isFirst?: boolean;
  isLast?: boolean;
}

export default function MenuItem({
  text,
  icon,
  href,
  onClick,
  fontWeight = 500,
  badge,
  isFirst = false,
  isLast = false,
}: MenuItemProps) {
  const fontWeightClass: Record<number, string | undefined> = {
    400: styles.fontNormal,
    500: styles.fontMedium,
    600: styles.fontSemibold,
  };

  const borderRadiusClass =
    isFirst && isLast
      ? styles.radiusAll
      : isFirst
        ? styles.radiusTop
        : isLast
          ? styles.radiusBottom
          : undefined;

  const content = (
    <div className={cx(styles.container, borderRadiusClass)}>
      {/* Иконка */}
      {icon && <div className={cx(styles.c1, styles.tw1)}>{icon}</div>}

      {/* Текст */}
      <span className={cx(styles.text, fontWeightClass[fontWeight])}>{text}</span>

      {/* Стрелка */}
      <img
        src="/icons/global/Wrap-Profile.svg"
        alt="arrow"
        className={cx(styles.c2, styles.tw2)}
      />

      {/* Бейдж */}
      {badge !== undefined && (
        <div className={cx(styles.c3, styles.tw3)}>
          <span className={styles.c4}>{badge}</span>
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className={styles.link}>
        {content}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button onClick={onClick} className={styles.c5}>
        {content}
      </button>
    );
  }

  return content;
}
