"use client";
import React from "react";
import MenuItem from "./ProfileMenuItem";
import styles from "./ProfileMenuSection.module.css";
import cx from "clsx";

interface MenuItemData {
  text: string;
  icon?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  fontWeight?: 400 | 500 | 600;
  badge?: string | number;
}

interface MenuSectionProps {
  items: MenuItemData[];
  className?: string;
}

export default function MenuSection({ items, className = "" }: MenuSectionProps) {
  return (
    <div className={cx(styles.root, className)}>
      {items.map((item, index) => (
        <MenuItem
          key={index}
          {...item}
          isFirst={index === 0}
          isLast={index === items.length - 1}
        />
      ))}
    </div>
  );
}
