'use client'
import React from 'react';
import { Search } from 'lucide-react';
import styles from './BrandsSearch.module.css';
import cx from 'clsx';

export default function BrandsSearch({ value, onChange, placeholder = 'Найти бренд' }) {
  return (
    <div className={cx(styles.c1, styles.tw1)}>
      <div className={cx(styles.c2, styles.tw2)}>
        <Search size={17.49} className={styles.c3} strokeWidth={1.92} />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={cx(styles.c4, styles.tw3)}
        />
      </div>
    </div>
  );
}

