'use client';
import React, { useMemo, useState } from 'react';
import styles from './BrandCard.module.css';
import { cn as cx } from '@/shared/lib/ui-utils';

function getInitial(name) {
  const trimmed = typeof name === 'string' ? name.trim() : '';
  if (!trimmed) return '?';
  return trimmed.charAt(0).toUpperCase();
}

function ImgWithFallback({ src, fallbacks, alt, className, onAllFailed }) {
  const sources = useMemo(
    () =>
      [src, ...(Array.isArray(fallbacks) ? fallbacks : [])].filter(
        (s) => typeof s === 'string' && s.trim()
      ),
    [src, fallbacks]
  );
  const [idx, setIdx] = useState(0);
  const [allFailed, setAllFailed] = useState(false);
  const current = sources[idx];

  if (!current || allFailed) return null;

  return (
    <img
      src={current}
      alt={alt}
      className={className}
      onError={() => {
        if (idx < sources.length - 1) {
          setIdx(idx + 1);
        } else {
          setAllFailed(true);
          onAllFailed?.();
        }
      }}
    />
  );
}

export default function BrandCard({ id, name, image, imageFallbacks, onClick }) {
  const [imageFailed, setImageFailed] = useState(false);
  const hasImage = Boolean(image) && !imageFailed && !!String(image).trim();

  return (
    <li
      className={cx(styles.c1, styles.tw1)}
      onClick={() => onClick?.(id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.(id);
        }
      }}
    >
      <div className={cx(styles.c2, styles.tw2)}>
        <div className={cx(styles.c3, styles.tw3)}>
          {hasImage ? (
            <ImgWithFallback
              src={image}
              fallbacks={imageFallbacks}
              alt={name}
              className={styles.c4}
              onAllFailed={() => setImageFailed(true)}
            />
          ) : (
            <span className={styles.fallbackInitial} aria-hidden="true">
              {getInitial(name)}
            </span>
          )}
        </div>

        <div className={cx(styles.c5, styles.tw4)}>
          <span className={styles.c6}>{name}</span>
          <span className={styles.c7}>Бренд</span>
        </div>
      </div>

      <img
        src="/icons/global/Wrap.svg"
        alt=""
        aria-hidden="true"
        className={cx(styles.c8, styles.tw5)}
      />
    </li>
  );
}
