'use client'
import React from 'react';
import MenuItem from './ProfileMenuItem';
import styles from './ProfileMenuSection.module.css';
import cx from 'clsx';

export default function MenuSection({ items, className = '' }) {
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

