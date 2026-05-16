'use client';
import React, { useMemo, useState } from 'react';
import styles from './BrandCard.module.css';
import cx from 'clsx';

/**
 * Brendning birinchi alifbe harfini chiqaruvchi helper. Logo URL ishlamasa
 * (yoki backend `logoUrl: null` qaytarsa), broken-image ikonka o'rniga
 * toza letter-circle ko'rsatamiz — dizayn screenshotidagi clean fallback.
 */
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

export default function BrandCard({
  name,
  image,
  imageFallbacks,
  isFavorite = false,
  onToggleFavorite,
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const hasImage = Boolean(image) && !imageFailed && !!String(image).trim();

  return (
    <div className={cx(styles.c1, styles.tw1)}>
      <div className={cx(styles.c2, styles.tw2)}>
        {hasImage ? (
          <ImgWithFallback
            src={image}
            fallbacks={imageFallbacks}
            alt={name}
            className={styles.c3}
            onAllFailed={() => setImageFailed(true)}
          />
        ) : (
          <span className={styles.fallbackInitial} aria-hidden="true">
            {getInitial(name)}
          </span>
        )}
      </div>

      <div className={cx(styles.c4, styles.tw3)}>
        <span className={styles.c5}>{name}</span>
        <span className={styles.c6}>Бренд</span>
      </div>

      <button
        type="button"
        onClick={onToggleFavorite}
        className={cx(styles.c7, styles.tw4)}
        aria-pressed={isFavorite}
        aria-label={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
      >
        <img
          src={isFavorite ? '/icons/global/active-heart.svg' : '/icons/global/not-active-heart.svg'}
          alt=""
          aria-hidden="true"
          className={styles.c8}
        />
      </button>
    </div>
  );
}
